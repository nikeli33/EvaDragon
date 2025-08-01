import sys
import os
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QMessageBox,
    QDialog, QLineEdit, QVBoxLayout, QHBoxLayout
)
from PyQt5.QtGui import QPixmap, QIcon, QFont, QPalette, QBrush
from PyQt5.QtCore import Qt, QUrl, QProcess
from PyQt5.QtMultimedia import QSoundEffect
from typing import Optional

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class ModelInstallDialog(QDialog):
    """
    Диалог для ввода названия модели и её установки через docker exec ollama ollama pull <model>.
    """
    def __init__(self, owner: Optional[QWidget] = None):
        super().__init__(owner)
        self.owner: Optional[QWidget] = owner  # ссылка на главное окно, чтобы обновлять его status_label
        self.setWindowTitle("Установка модели")
        self.setFixedSize(400, 150)

        # Основные виджеты
        self.input_label = QLabel("Введите название модели (например: deepseek-r1:7b):", self)
        self.model_input = QLineEdit(self)
        self.model_input.setPlaceholderText("Название модели")
        self.install_button = QPushButton("Установить", self)
        self.install_button.setFont(QFont("Segoe UI", 10))
        # Стиль кнопки — можно настроить по желанию
        self.install_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 128, 180);
                color: white;
                border-radius: 8px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 200, 200);
            }
            QPushButton:pressed {
                background-color: rgba(0, 0, 100, 200);
            }
        """)
        self.status_label = QLabel("", self)
        self.status_label.setWordWrap(True)

        # Layout
        v_layout = QVBoxLayout()
        v_layout.addWidget(self.input_label)
        v_layout.addWidget(self.model_input)
        # Кнопка по центру
        h_btn = QHBoxLayout()
        h_btn.addStretch(1)
        h_btn.addWidget(self.install_button)
        h_btn.addStretch(1)
        v_layout.addLayout(h_btn)
        v_layout.addWidget(self.status_label)
        self.setLayout(v_layout)

        # Подключаем события
        self.install_button.clicked.connect(self.on_click_install)

        # QProcess для установки
        self.proc_check = None
        self.proc_pull = None

        # Буферы для логов (если требуется)
        self.pull_log = ""
        self.pull_log_err = ""

    def on_click_install(self):
        model_name = self.model_input.text().strip()
        if not model_name:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, введите название модели")
            return

        # Блокируем ввод и кнопку
        self.install_button.setEnabled(False)
        self.model_input.setEnabled(False)
        self.status_label.setText("⏳ Проверка контейнера ollama...")
        # Обновляем главный статус
        if self.owner and hasattr(self.owner, 'status_label'):
            self.owner.status_label.setText(f"⏳ Проверка контейнера ollama для установки модели {model_name}...")

        # Проверка, что контейнер ollama запущен
        self.proc_check = QProcess(self)
        # Сигнал finished срабатывает, когда процесс завершён
        self.proc_check.finished.connect(lambda exitCode, exitStatus: self.on_check_finished(exitCode, exitStatus, model_name))
        # Запускаем: docker ps --filter name=ollama --filter status=running --format {{.Names}}
        self.proc_check.start("docker", ["ps", "--filter", "name=ollama", "--filter", "status=running", "--format", "{{.Names}}"])

    def on_check_finished(self, exitCode, exitStatus, model_name):
        # Читаем вывод
        out = ""
        if self.proc_check:
            out = self.proc_check.readAllStandardOutput().data().decode().strip()
        # Сбросим proc_check
        self.proc_check = None

        if "ollama" not in out:
            # Контейнер не запущен
            self.status_label.setText("❌ Контейнер ollama не запущен. Сначала запустите n8n или контейнер ollama вручную.")
            if self.owner and hasattr(self.owner, 'status_label'):
                self.owner.status_label.setText("❌ Контейнер ollama не запущен. Сначала запустите n8n или контейнер ollama вручную.")
            QMessageBox.warning(self, "Контейнер не запущен",
                                "Контейнер ollama не запущен.\nСначала нажмите «Запустить n8n» или запустите контейнер ollama.")
            # Разблокируем ввод
            self.install_button.setEnabled(True)
            self.model_input.setEnabled(True)
            return

        # Если контейнер запущен, начинаем установку
        self.status_label.setText(f"⏳ Устанавливается модель {model_name}...")
        if self.owner and hasattr(self.owner, 'status_label'):
            self.owner.status_label.setText(f"⏳ Устанавливается модель {model_name}...")

        # Подготовка буферов
        self.pull_log = ""
        self.pull_log_err = ""
        # Запуск процесса pull
        self.proc_pull = QProcess(self)
        # Чтобы читать stdout и stderr отдельно, не объединяем:
        # self.proc_pull.setProcessChannelMode(QProcess.MergedChannels)
        self.proc_pull.readyReadStandardOutput.connect(self.on_pull_output)
        self.proc_pull.readyReadStandardError.connect(self.on_pull_error)
        self.proc_pull.finished.connect(lambda exitCode, exitStatus: self.on_pull_finished(exitCode, exitStatus, model_name))
        # Команда: docker exec ollama ollama pull <model_name>
        # Без "-it", т.к. интерактивность не нужна
        self.proc_pull.start("docker", ["exec", "ollama", "ollama", "pull", model_name])

    def on_pull_output(self):
        if not self.proc_pull:
            return
        data = self.proc_pull.readAllStandardOutput().data().decode()
        self.pull_log += data
        # Кратко обновлять статус — можно, но чтобы не мигало слишком часто, обновляем только последнее непустое сообщение
        last_lines = [line for line in data.splitlines() if line.strip()]
        if last_lines:
            last_line = last_lines[-1]
            # Обновляем диалоговый статус и главный
            self.status_label.setText(f"… {last_line}")
            if self.owner and hasattr(self.owner, 'status_label'):
                self.owner.status_label.setText(f"… {last_line}")

    def on_pull_error(self):
        if not self.proc_pull:
            return
        data = self.proc_pull.readAllStandardError().data().decode()
        self.pull_log_err += data
        # Можно не обновлять GUI на каждую ошибку, оставим обработку в on_pull_finished

    def on_pull_finished(self, exitCode, exitStatus, model_name):
        # Процесс установки завершён
        success = (exitCode == 0)
        if success:
            self.status_label.setText(f"✅ Модель {model_name} успешно установлена или уже была установлена")
            if self.owner and hasattr(self.owner, 'status_label'):
                self.owner.status_label.setText(f"✅ Модель {model_name} успешно установлена или уже была установлена")
        else:
            self.status_label.setText(f"❌ Ошибка установки модели {model_name}")
            if self.owner and hasattr(self.owner, 'status_label'):
                self.owner.status_label.setText(f"❌ Ошибка установки модели {model_name}")
            # Показать подробности
            detail = ""
            if self.pull_log_err:
                detail = self.pull_log_err
            elif self.pull_log:
                detail = self.pull_log
            else:
                detail = f"Код выхода: {exitCode}"
            # Ограничить длину, если очень большой
            if len(detail) > 1000:
                detail = detail[:1000] + "\n…"
            msg = QMessageBox(self)
            msg.setWindowTitle("Ошибка установки модели")
            msg.setText(f"Не удалось установить модель {model_name}.")
            msg.setDetailedText(detail)
            msg.setIcon(QMessageBox.Critical)
            msg.exec_()

        # Сбросим состояние, разблокируем ввод
        self.install_button.setEnabled(True)
        self.model_input.setEnabled(True)
        # Сброс буферов
        self.pull_log = ""
        self.pull_log_err = ""
        self.proc_pull = None

class ModelDeleteDialog(QDialog):
    """
    Диалог для удаления модели: docker exec ollama ollama rm <model_name>
    """
    def __init__(self, owner: Optional[QWidget] = None):
        super().__init__(owner)
        self.owner: Optional[QWidget] = owner  # главное окно для обновления status_label
        self.setWindowTitle("Удаление модели")
        self.setFixedSize(400, 150)

        # Виджеты
        self.input_label = QLabel("Введите название модели для удаления (например: deepseek-r1:7b):", self)
        self.model_input = QLineEdit(self)
        self.model_input.setPlaceholderText("Название модели")
        self.delete_button = QPushButton("Удалить", self)
        self.delete_button.setFont(QFont("Segoe UI", 10))
        self.delete_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(128, 0, 0, 180);
                color: white;
                border-radius: 8px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: rgba(200, 0, 0, 200);
            }
            QPushButton:pressed {
                background-color: rgba(100, 0, 0, 200);
            }
        """)
        self.status_label = QLabel("", self)
        self.status_label.setWordWrap(True)

        # Layout
        v_layout = QVBoxLayout()
        v_layout.addWidget(self.input_label)
        v_layout.addWidget(self.model_input)
        h_btn = QHBoxLayout()
        h_btn.addStretch(1)
        h_btn.addWidget(self.delete_button)
        h_btn.addStretch(1)
        v_layout.addLayout(h_btn)
        v_layout.addWidget(self.status_label)
        self.setLayout(v_layout)

        # Сигнал кнопки
        self.delete_button.clicked.connect(self.on_click_delete)

        # QProcess объекты
        self.proc_check = None
        self.proc_rm = None

        # Буферы логов
        self.rm_log = ""
        self.rm_log_err = ""

    def on_click_delete(self):
        model_name = self.model_input.text().strip()
        if not model_name:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, введите название модели")
            return

        # Блокируем ввод
        self.delete_button.setEnabled(False)
        self.model_input.setEnabled(False)
        self.status_label.setText("⏳ Проверка контейнера ollama...")
        if self.owner and hasattr(self.owner, 'status_label'):
            self.owner.status_label.setText(f"⏳ Проверка контейнера ollama для удаления модели {model_name}...")

        # Проверка запущен ли контейнер ollama
        self.proc_check = QProcess(self)
        self.proc_check.finished.connect(lambda exitCode, exitStatus: self.on_check_finished(exitCode, exitStatus, model_name))
        self.proc_check.start("docker", ["ps", "--filter", "name=ollama", "--filter", "status=running", "--format", "{{.Names}}"])

    def on_check_finished(self, exitCode, exitStatus, model_name):
        out = ""
        if self.proc_check:
            out = self.proc_check.readAllStandardOutput().data().decode().strip()
        self.proc_check = None

        if "ollama" not in out:
            # Контейнер не запущен
            self.status_label.setText("❌ Контейнер ollama не запущен. Сначала запустите n8n или контейнер ollama.")
            if self.owner and hasattr(self.owner, 'status_label'):
                self.owner.status_label.setText("❌ Контейнер ollama не запущен. Сначала запустите n8n или контейнер ollama.")
            QMessageBox.warning(self, "Контейнер не запущен",
                                "Контейнер ollama не запущен.\nСначала нажмите «Запустить n8n» или запустите контейнер ollama.")
            # Разблокируем ввод
            self.delete_button.setEnabled(True)
            self.model_input.setEnabled(True)
            return

        # Запускаем удаление
        self.status_label.setText(f"⏳ Удаляется модель {model_name}...")
        if self.owner and hasattr(self.owner, 'status_label'):
            self.owner.status_label.setText(f"⏳ Удаляется модель {model_name}...")

        self.rm_log = ""
        self.rm_log_err = ""
        self.proc_rm = QProcess(self)
        self.proc_rm.readyReadStandardOutput.connect(self.on_rm_output)
        self.proc_rm.readyReadStandardError.connect(self.on_rm_error)
        self.proc_rm.finished.connect(lambda exitCode, exitStatus: self.on_rm_finished(exitCode, exitStatus, model_name))
        # Команда: docker exec ollama ollama rm <model_name>
        self.proc_rm.start("docker", ["exec", "ollama", "ollama", "rm", model_name])

    def on_rm_output(self):
        if not self.proc_rm:
            return
        data = self.proc_rm.readAllStandardOutput().data().decode()
        self.rm_log += data
        # Отображаем последнюю строку, если есть
        lines = [line for line in data.splitlines() if line.strip()]
        if lines:
            last_line = lines[-1]
            self.status_label.setText(f"… {last_line}")
            if self.owner and hasattr(self.owner, 'status_label'):
                self.owner.status_label.setText(f"… {last_line}")

    def on_rm_error(self):
        if not self.proc_rm:
            return
        data = self.proc_rm.readAllStandardError().data().decode()
        self.rm_log_err += data

    def on_rm_finished(self, exitCode, exitStatus, model_name):
        success = (exitCode == 0)
        if success:
            # Обычно команда выводит что-то вроде "deleted 'MODEL_NAME'"
            self.status_label.setText(f"✅ Модель {model_name} успешно удалена")
            if self.owner and hasattr(self.owner, 'status_label'):
                self.owner.status_label.setText(f"✅ Модель {model_name} успешно удалена")
        else:
            self.status_label.setText(f"❌ Ошибка удаления модели {model_name}")
            if self.owner and hasattr(self.owner, 'status_label'):
                self.owner.status_label.setText(f"❌ Ошибка удаления модели {model_name}")
            # Детали ошибки
            detail = ""
            if self.rm_log_err:
                detail = self.rm_log_err
            elif self.rm_log:
                detail = self.rm_log
            else:
                detail = f"Код выхода: {exitCode}"
            if len(detail) > 1000:
                detail = detail[:1000] + "\n…"
            msg = QMessageBox(self)
            msg.setWindowTitle("Ошибка удаления модели")
            msg.setText(f"Не удалось удалить модель {model_name}.")
            msg.setDetailedText(detail)
            msg.setIcon(QMessageBox.Critical)
            msg.exec_()

        # Сброс и разблокировка
        self.delete_button.setEnabled(True)
        self.model_input.setEnabled(True)
        self.rm_log = ""
        self.rm_log_err = ""
        self.proc_rm = None

class SettingsDialog(QDialog):
    """
    Диалог «Настройки», содержащий кнопки для установки/удаления модели и будущие опции.
    """
    def __init__(self, owner: Optional[QWidget] = None):
        super().__init__(owner)
        self.owner: Optional[QWidget] = owner  # главное окно (N8nGUI), чтобы передавать как parent в другие диалоги
        self.setWindowTitle("Настройки")
        self.setFixedSize(300, 200)

        # Кнопки внутри диалога
        self.install_btn = QPushButton("📥 Установить модель...", self)
        self.install_btn.setFont(QFont("Segoe UI", 10))
        self.install_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 128, 180);
                color: white;
                border-radius: 8px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 200, 200);
            }
            QPushButton:pressed {
                background-color: rgba(0, 0, 100, 200);
            }
        """)
        self.delete_btn = QPushButton("🗑️ Удалить модель...", self)
        self.delete_btn.setFont(QFont("Segoe UI", 10))
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(128, 0, 0, 180);
                color: white;
                border-radius: 8px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: rgba(200, 0, 0, 200);
            }
            QPushButton:pressed {
                background-color: rgba(100, 0, 0, 200);
            }
        """)
        # Заготовка для будущих настроек Cloudflare
        self.cloudflare_btn = QPushButton("☁️ Настройки Cloudflare...", self)
        self.cloudflare_btn.setFont(QFont("Segoe UI", 10))
        # Пока неактивна
        self.cloudflare_btn.setEnabled(False)
        self.cloudflare_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 128, 128, 180);
                color: white;
                border-radius: 8px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: rgba(0, 200, 200, 200);
            }
            QPushButton:pressed {
                background-color: rgba(0, 100, 100, 200);
            }
        """)

        # Layout
        v_layout = QVBoxLayout()
        v_layout.addWidget(self.install_btn)
        v_layout.addWidget(self.delete_btn)
        v_layout.addWidget(self.cloudflare_btn)
        v_layout.addStretch(1)
        self.setLayout(v_layout)

        # Сигналы кнопок
        self.install_btn.clicked.connect(self.open_install)
        self.delete_btn.clicked.connect(self.open_delete)
        # self.cloudflare_btn.clicked.connect(self.open_cloudflare_settings)  # в будущем

    def open_install(self):
        # Открываем диалог установки модели
        dlg = ModelInstallDialog(owner=self.owner)
        dlg.exec_()

    def open_delete(self):
        # Открываем диалог удаления модели
        dlg = ModelDeleteDialog(owner=self.owner)
        dlg.exec_()

    # В будущем можно добавить метод open_cloudflare_settings здесь

class N8nGUI(QWidget):
    def __init__(self):
        super().__init__()
        # Звуковые эффекты
        self.hover_sound = QSoundEffect()
        self.hover_sound.setSource(QUrl.fromLocalFile(resource_path("assets/hover.wav")))
        self.hover_sound.setVolume(0.25)

        self.click_sound = QSoundEffect()
        self.click_sound.setSource(QUrl.fromLocalFile(resource_path("assets/click.wav")))
        self.click_sound.setVolume(0.25)

        # Настройки окна
        self.setWindowTitle("Eva: Red Dragon")
        self.setFixedSize(800, 600)
        self.setWindowIcon(QIcon(resource_path("assets/icon.ico")))

        # Фоновое изображение
        bg_path = resource_path("assets/background.jpg")
        if os.path.exists(bg_path):
            bg_pixmap = QPixmap(bg_path).scaled(self.size(), Qt.KeepAspectRatioByExpanding)
            palette = QPalette()
            palette.setBrush(QPalette.Window, QBrush(bg_pixmap))
            self.setPalette(palette)

        # Смещение по Y (все три кнопки сдвинем на +30px вниз)
        offset = 30

        # Кнопка запуска
        self.start_button = QPushButton("🚀 Запустить n8n", self)
        # Было (280, 350, 240, 40) → стало (280, 380, 240, 40)
        self.start_button.setGeometry(280, 350 + offset, 240, 40)
        self.start_button.setFont(QFont("Segoe UI", 10))
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 128, 0, 180);
                color: white;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: rgba(0, 170, 0, 200);
            }
            QPushButton:pressed {
                background-color: rgba(0, 100, 0, 200);
            }
        """)
        self.start_button.clicked.connect(self.start_n8n)
        self.start_button.installEventFilter(self)

        # Кнопка остановки
        self.stop_button = QPushButton("🛑 Остановить всё", self)
        # Было (280, 400, 240, 40) → стало (280, 430, 240, 40)
        self.stop_button.setGeometry(280, 400 + offset, 240, 40)
        self.stop_button.setFont(QFont("Segoe UI", 10))
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(200, 0, 0, 180);
                color: white;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: rgba(255, 50, 50, 200);
            }
            QPushButton:pressed {
                background-color: rgba(150, 0, 0, 200);
            }
        """)
        self.stop_button.clicked.connect(self.stop_processes)
        self.stop_button.installEventFilter(self)

        # Кнопка открытия диалога «Настройки»
        self.settings_button = QPushButton("⚙️ Настройки", self)
        # Было (280, 450, 240, 40) → стало (280, 480, 240, 40)
        self.settings_button.setGeometry(280, 450 + offset, 240, 40)
        self.settings_button.setFont(QFont("Segoe UI", 10))
        self.settings_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 128, 180);
                color: white;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 200, 200);
            }
            QPushButton:pressed {
                background-color: rgba(0, 0, 100, 200);
            }
        """)
        self.settings_button.clicked.connect(self.open_settings_dialog)
        self.settings_button.installEventFilter(self)

        # Статус
        self.status_label = QLabel("Готов к работе", self)
        # Оставляем статус на прежнем месте (0,550), т.к. сдвигали только три кнопки
        self.status_label.setGeometry(0, 550, 800, 30)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Segoe UI", 10))
        self.status_label.setStyleSheet("color: white; background-color: rgba(0, 0, 0, 100);")

        # Определяем корневую директорию проекта
        if getattr(sys, "frozen", False):
            # Если запущен как скомпилированный .exe (PyInstaller)
            base_dir = os.path.dirname(sys.executable)
            self.project_root = os.path.abspath(os.path.join(base_dir, ".."))
        else:
            # Если запущен как скрипт python gui.py
            self.project_root = os.path.dirname(os.path.abspath(__file__))

    def eventFilter(self, source, event):
        if event.type() == event.Enter and isinstance(source, QPushButton):
            self.hover_sound.play()
        elif event.type() == event.MouseButtonPress and isinstance(source, QPushButton):
            self.click_sound.play()
        return super().eventFilter(source, event)

    def start_n8n(self):
        try:
            # Запуск без Cloudflare тоннеля
            subprocess.Popen('cmd /c start "" "start_n8n.cmd"', cwd=self.project_root, shell=True)
            self.status_label.setText("⏳ Запуск n8n через localhost...")
        except Exception as e:
            self.status_label.setText(f"❌ Ошибка запуска: {e}")

    def stop_processes(self):
        try:
            # Не убиваем cloudflared.exe, так как он не запускается
            subprocess.call(f'docker compose -f "{os.path.join(self.project_root, "docker-compose.yml")}" down', shell=True)
            self.status_label.setText("✅ Все процессы остановлены")
        except Exception as e:
            self.status_label.setText(f"❌ Ошибка остановки: {e}")

    def open_settings_dialog(self):
        """
        Открывает диалог «Настройки», где есть кнопки установки/удаления модели.
        """
        dlg = SettingsDialog(owner=self)
        dlg.exec_()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = N8nGUI()
    window.show()
    sys.exit(app.exec_())
