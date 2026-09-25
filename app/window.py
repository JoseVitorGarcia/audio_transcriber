from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.engine import load_model, transcribe_file
from src.paths import resource_dir

AUDIO_EXTS = (".mp3", ".wav", ".m4a", ".flac", ".ogg", ".mp4", ".aac", ".wma", ".opus")

STATUS_TEXT = {
    "queued": "Na fila",
    "running": "Transcrevendo...",
    "done": "Concluído",
    "error": "Erro",
}


class Worker(QObject):
    model_loaded = Signal()
    started = Signal(int)
    progress = Signal(int, int)
    finished_file = Signal(int, str)
    failed = Signal(int, str)
    all_done = Signal()

    def __init__(self, jobs):
        super().__init__()
        self.jobs = jobs
        self._cancel = False
        self._model = None

    def cancel(self):
        self._cancel = True

    def run(self):
        try:
            if self._model is None:
                self._model = load_model("medium")
        except Exception as e:
            for job_id, _ in self.jobs:
                self.failed.emit(job_id, f"Falha ao carregar o modelo: {e}")
            self.all_done.emit()
            return
        self.model_loaded.emit()

        for job_id, path in self.jobs:
            if self._cancel:
                break
            self.started.emit(job_id)
            try:
                text = transcribe_file(
                    self._model,
                    path,
                    on_progress=lambda p, j=job_id: self.progress.emit(j, int(p * 100)),
                    should_cancel=lambda: self._cancel,
                )
                self.finished_file.emit(job_id, text)
            except InterruptedError:
                break
            except Exception as e:
                self.failed.emit(job_id, str(e))
        self.all_done.emit()


class DropList(QListWidget):
    files_dropped = Signal(list)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        e.acceptProposedAction()

    def dropEvent(self, e):
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        self.files_dropped.emit(paths)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Transcritor de Áudio")
        self.resize(980, 620)

        self.jobs = {}
        self.next_id = 0
        self.thread = None
        self.worker = None

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        top = QHBoxLayout()
        self.btn_add = QPushButton("Adicionar áudios...")
        self.btn_add.clicked.connect(self.pick_files)
        self.btn_clear = QPushButton("Limpar concluídos")
        self.btn_clear.clicked.connect(self.clear_finished)
        top.addWidget(self.btn_add)
        top.addWidget(self.btn_clear)
        top.addStretch()
        root.addLayout(top)

        split = QSplitter(Qt.Horizontal)
        root.addWidget(split, 1)

        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        self.list = DropList()
        self.list.files_dropped.connect(self.add_files)
        self.list.currentItemChanged.connect(self.show_current)
        lv.addWidget(QLabel("Arquivos (arraste áudios para cá)"))
        lv.addWidget(self.list, 1)
        split.addWidget(left)

        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        self.title = QLabel("Selecione um arquivo")
        self.title.setStyleSheet("font-weight: 600;")
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setPlaceholderText("A transcrição aparecerá aqui.")
        buttons = QHBoxLayout()
        self.btn_copy = QPushButton("Copiar texto")
        self.btn_copy.clicked.connect(self.copy_text)
        self.btn_save = QPushButton("Baixar .txt")
        self.btn_save.clicked.connect(self.save_text)
        buttons.addWidget(self.btn_copy)
        buttons.addWidget(self.btn_save)
        buttons.addStretch()
        rv.addWidget(self.title)
        rv.addWidget(self.text, 1)
        rv.addLayout(buttons)
        split.addWidget(right)
        split.setSizes([340, 640])

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setVisible(False)
        self.status = QLabel("Pronto. Adicione arquivos de áudio para começar.")
        root.addWidget(self.bar)
        root.addWidget(self.status)

        self.update_buttons()

    def pick_files(self):
        exts = " ".join(f"*{e}" for e in AUDIO_EXTS)
        paths, _ = QFileDialog.getOpenFileNames(self, "Escolher áudios", "", f"Áudios ({exts})")
        if paths:
            self.add_files(paths)

    def add_files(self, paths):
        new = []
        for p in paths:
            if not p.lower().endswith(AUDIO_EXTS):
                continue
            job_id = self.next_id
            self.next_id += 1
            item = QListWidgetItem()
            item.setData(Qt.UserRole, job_id)
            self.jobs[job_id] = {"path": p, "status": "queued", "text": "", "item": item, "error": ""}
            self.list.addItem(item)
            self.refresh_item(job_id)
            new.append((job_id, p))
        if not new:
            return
        if self.list.currentItem() is None:
            self.list.setCurrentRow(0)
        self.pending = getattr(self, "pending", []) + new
        self.start_if_idle()

    def start_if_idle(self):
        if self.thread is not None or not self.pending:
            return
        jobs, self.pending = self.pending, []
        self.thread = QThread()
        self.worker = Worker(jobs)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.started.connect(self.on_started)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished_file.connect(self.on_finished)
        self.worker.failed.connect(self.on_failed)
        self.worker.model_loaded.connect(lambda: self.status.setText("Transcrevendo..."))
        self.worker.all_done.connect(self.on_all_done)
        self.status.setText("Carregando modelo (pode levar alguns segundos)...")
        self.bar.setRange(0, 0)
        self.bar.setVisible(True)
        self.thread.start()

    def on_started(self, job_id):
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.jobs[job_id]["status"] = "running"
        self.refresh_item(job_id)
        self.status.setText(f"Transcrevendo: {Path(self.jobs[job_id]['path']).name}")

    def on_progress(self, job_id, pct):
        self.bar.setValue(pct)
        self.refresh_item(job_id, pct)

    def on_finished(self, job_id, text):
        self.jobs[job_id].update(status="done", text=text)
        self.refresh_item(job_id)
        self.refresh_view()

    def on_failed(self, job_id, msg):
        self.jobs[job_id].update(status="error", error=msg)
        self.refresh_item(job_id)
        self.refresh_view()

    def on_all_done(self):
        self.thread.quit()
        self.thread.wait()
        self.thread = None
        self.worker = None
        self.bar.setVisible(False)
        self.status.setText("Pronto.")
        self.start_if_idle()

    def refresh_item(self, job_id, pct=None):
        j = self.jobs[job_id]
        label = STATUS_TEXT[j["status"]]
        if j["status"] == "running" and pct is not None:
            label = f"Transcrevendo... {pct}%"
        j["item"].setText(f"{Path(j['path']).name}\n{label}")

    def current_job(self):
        item = self.list.currentItem()
        return self.jobs.get(item.data(Qt.UserRole)) if item else None

    def show_current(self, *_):
        self.refresh_view()

    def refresh_view(self):
        j = self.current_job()
        if not j:
            self.title.setText("Selecione um arquivo")
            self.text.clear()
        else:
            self.title.setText(Path(j["path"]).name)
            if j["status"] == "done":
                self.text.setPlainText(j["text"])
            elif j["status"] == "error":
                self.text.setPlainText(f"Não foi possível transcrever este arquivo.\n\n{j['error']}")
            else:
                self.text.setPlainText("")
        self.update_buttons()

    def update_buttons(self):
        j = self.current_job()
        ok = bool(j and j["status"] == "done")
        self.btn_copy.setEnabled(ok)
        self.btn_save.setEnabled(ok)

    def copy_text(self):
        j = self.current_job()
        if j and j["text"]:
            QApplication.clipboard().setText(j["text"])
            self.status.setText("Texto copiado.")

    def save_text(self):
        j = self.current_job()
        if not j or not j["text"]:
            return
        default = str(Path(j["path"]).with_suffix(".txt"))
        path, _ = QFileDialog.getSaveFileName(self, "Salvar transcrição", default, "Texto (*.txt)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(j["text"])
            self.status.setText(f"Salvo em {path}")

    def clear_finished(self):
        for job_id in [k for k, v in self.jobs.items() if v["status"] in ("done", "error")]:
            row = self.list.row(self.jobs[job_id]["item"])
            self.list.takeItem(row)
            del self.jobs[job_id]
        self.refresh_view()

    def closeEvent(self, e):
        if self.thread is not None:
            r = QMessageBox.question(
                self, "Sair", "Há transcrições em andamento. Deseja cancelar e sair?"
            )
            if r != QMessageBox.Yes:
                e.ignore()
                return
            self.worker.cancel()
            self.thread.quit()
            self.thread.wait(5000)
        e.accept()


def run():
    app = QApplication([])
    app.setApplicationName("Transcritor de Áudio")
    icon = resource_dir() / "assets" / "icon.ico"
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))
    win = MainWindow()
    win.show()
    app.exec()
