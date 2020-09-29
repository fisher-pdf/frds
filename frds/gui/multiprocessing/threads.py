from PyQt5 import QtCore

from frds.settings import MAX_WORKERS, PROGRESS_UPDATE_INTERVAL_SECONDS
from frds.gui.multiprocessing import (
    STATUS_ERROR,
    STATUS_COMPLETE,
    DEFAULT_STATE,
)


class ThreadsManager(QtCore.QAbstractListModel):
    """
    Manager to handle our worker queues and state.
    Also functions as a Qt data model for a view
    displaying progress for each worker.

    """

    _workers = {}
    _state = {}

    status = QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__()

        # Create a threadpool for our workers.
        self.threadpool = QtCore.QThreadPool()
        self.threadpool.setMaxThreadCount(MAX_WORKERS)
        self.max_threads = self.threadpool.maxThreadCount()
        print("Multithreading with maximum %d threads" % self.max_threads)

        self.status_timer = QtCore.QTimer()
        self.status_timer.setInterval(PROGRESS_UPDATE_INTERVAL_SECONDS)
        self.status_timer.timeout.connect(self.notify_status)
        self.status_timer.start()

    def notify_status(self):
        n_workers = len(self._workers)
        running = min(n_workers, self.max_threads)
        waiting = max(0, n_workers - self.max_threads)
        self.status.emit(
            "{} running, {} waiting, {} threads".format(
                running, waiting, self.max_threads
            )
        )

    def enqueue(self, worker):
        """
        Enqueue a worker to run (at some point) by passing it to the QThreadPool.
        """
        worker.signals.error.connect(self.receive_error)
        worker.signals.status.connect(self.receive_status)
        worker.signals.progress.connect(self.receive_progress)
        worker.signals.finished.connect(self.done)

        self.threadpool.start(worker)
        self._workers[worker.job_id] = worker

        # Set default status to waiting, 0 progress.
        self._state[worker.job_id] = DEFAULT_STATE.copy()

        self.layoutChanged.emit()

    def receive_status(self, job_id, status):
        self._state[job_id]["status"] = status
        self.layoutChanged.emit()

    def receive_progress(self, job_id, progress):
        self._state[job_id]["progress"] = progress
        self.layoutChanged.emit()

    def receive_error(self, job_id, message):
        print(job_id, message)

    def done(self, job_id):
        """
        Task/worker complete. Remove it from the active workers
        dictionary. We leave it in worker_state, as this is used to
        to display past/complete workers too.
        """
        del self._workers[job_id]
        self.layoutChanged.emit()

    def cleanup(self):
        """
        Remove any complete/failed workers from worker_state.
        """
        for job_id, state in list(self._state.items()):
            if state["status"] in (STATUS_COMPLETE, STATUS_ERROR):
                del self._state[job_id]
        self.layoutChanged.emit()

    # Model interface
    def data(self, index, role):
        if role == QtCore.Qt.DisplayRole:
            # See below for the data structure.
            job_ids = list(self._state.keys())
            job_id = job_ids[index.row()]
            return job_id, self._state[job_id]

    def rowCount(self, index):
        return len(self._state)