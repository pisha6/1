"""
Логика 1-го задания: алгоритм Деккера.

Задание:
1) Первый поток считает сумму сегодняшней даты и времени (г+м+д+ч+мин+с)
   и записывает её в таблицу.
2) Второй поток проверяет, чётное ли число записано в таблице:
   если чётное -> пишет true, если нечётное -> пишет false.

Для взаимного исключения используется алгоритм Деккера (flag[2], turn).
"""

import datetime
import threading
import time


class DekkerShared:
    """Общие данные для двух потоков (таблица + переменные Деккера)."""

    def __init__(self):
        # Таблица/буфер результатов: каждый элемент это словарь
        # {"id": номер_записи, "sum": сумма_даты_времени, "even": True/False/None}
        self.table = []
        self.max_rows = 50      # ограничение на количество строк в окне
        self.next_id = 1        # следующий номер записи (растёт постоянно)
        self.pending = []       # очередь индексов строк, которые ещё не проверил поток 2

        # Переменные алгоритма Деккера
        self.flag = [False, False]  # флаги желания войти в критическую секцию
        self.turn = 1               # чей сейчас приоритет при конфликте

    def add_producer_result(self, sum_value):
        """Поток 1 записывает сумму в таблицу (результат появляется сразу)."""
        self.table.append({"id": self.next_id, "sum": sum_value, "even": None})
        self.next_id += 1

        # Запоминаем индекс новой строки, чтобы поток 2 мог её проверить
        new_row_index = len(self.table) - 1
        self.pending.append(new_row_index)

        # Если строк стало слишком много, удаляем самые старые из отображения
        if len(self.table) > self.max_rows:
            remove_count = len(self.table) - self.max_rows
            self.table = self.table[remove_count:]

            # После удаления сдвинулись индексы, поэтому поправляем очередь pending
            new_pending = []
            for index in self.pending:
                shifted_index = index - remove_count
                if shifted_index >= 0:
                    new_pending.append(shifted_index)
            self.pending = new_pending

    def add_checker_result(self, is_even):
        """Поток 2 записывает результат проверки чётности в первую необработанную строку."""
        if not self.pending:
            return

        index = self.pending.pop(0)
        if 0 <= index < len(self.table):
            self.table[index]["even"] = is_even

        # На всякий случай убираем возможные некорректные индексы
        self.pending = [i for i in self.pending if 0 <= i < len(self.table)]


class DekkerThread(threading.Thread):
    """
    Поток для 1-го задания.

    pid = 0 -> первый поток (считает сумму и записывает в таблицу)
    pid = 1 -> второй поток (проверяет чётность и дописывает true/false)
    """

    def __init__(self, pid, shared: DekkerShared, app):
        super().__init__(daemon=True)
        self.pid = pid
        self.shared = shared
        self.app = app

        # Управление потоком (кнопки Запуск/Пауза/Стоп и скорость)
        self.speed_delay = 1.0
        self._pause_event = threading.Event()
        self._pause_event.set()   # изначально поток "не на паузе"
        self._stop_event = threading.Event()

    # Методы управления потоком

    def pause(self):
        self._pause_event.clear()

    def resume(self):
        self._pause_event.set()

    def stop(self):
        self._stop_event.set()
        self._pause_event.set()  # чтобы поток не застрял в ожидании паузы

    def is_stopped(self):
        return self._stop_event.is_set()

    def wait_if_paused(self):
        """Ждём, пока пользователь снимет паузу (или пока не нажмут Стоп)."""
        while not self.is_stopped():
            if self._pause_event.is_set():
                return True
            time.sleep(0.05)
        return False

    def controlled_sleep(self, factor=1.0):
        """
        Задержка с учётом скорости, паузы и остановки.
        Делаем сон маленькими кусочками, чтобы интерфейс и кнопки реагировали быстро.
        """
        total_seconds = max(0.01, self.speed_delay * factor)
        end_time = time.time() + total_seconds

        while time.time() < end_time:
            if self.is_stopped():
                return False
            if not self._pause_event.is_set():
                if not self.wait_if_paused():
                    return False
            time.sleep(0.02)

        return not self.is_stopped()

    #ыГлавный цикл потока

    def run(self):
        if self.pid == 0:
            self.process0()
        else:
            self.process1()

    def process0(self):
        """
        Первый процесс (поток 1) по алгоритму Деккера.
        В критической секции он записывает сумму даты/времени в таблицу.
        """
        s = self.shared

        while not self.is_stopped():  # бесконечный цикл работы потока
            if not self.wait_if_paused():
                break

            # Подготовка данных (вне критической секции)
            now = datetime.datetime.now()
            sum_value = now.year + now.month + now.day + now.hour + now.minute + now.second

            #Вход в критическую секцию (алгоритм Деккера, процесс 0)
            s.flag[0] = True
            while s.flag[1]:
                if s.turn == 1:
                    s.flag[0] = False
                    while s.turn == 1:
                        if self.is_stopped():
                            s.flag[0] = False
                            return
                        # Если нажали паузу, временно снимаем флаг, чтобы не мешать другому потоку
                        if not self._pause_event.is_set():
                            s.flag[0] = False
                            if not self.wait_if_paused():
                                return
                            s.flag[0] = True
                            break
                        time.sleep(0.001)  # "ничего не делать"
                    else:
                        # turn изменился (теперь не 1)
                        s.flag[0] = True
                        continue
                    continue
                else:
                    if self.is_stopped():
                        s.flag[0] = False
                        return
                    time.sleep(0.001)

            # Критическая секция
            try:
                s.add_producer_result(sum_value)
            finally:
                # Выход из критической секции
                s.turn = 1
                s.flag[0] = False

            # Обновляем таблицу в интерфейсе сразу после записи
            self.app.ui_call(self.app.update_dekker_view)

            # Остальной код (задержка для регулировки скорости)
            if not self.controlled_sleep(1.0):
                break

    def process1(self):
        """
        Второй процесс (поток 2) по алгоритму Деккера.
        В критической секции он проверяет чётность и дописывает true/false.
        """
        s = self.shared

        while not self.is_stopped():
            if not self.wait_if_paused():
                break

            # Вход в критическую секцию (алгоритм Деккера, процесс 1)
            s.flag[1] = True
            while s.flag[0]:
                if s.turn == 0:
                    s.flag[1] = False
                    while s.turn == 0:
                        if self.is_stopped():
                            s.flag[1] = False
                            return
                        if not self._pause_event.is_set():
                            s.flag[1] = False
                            if not self.wait_if_paused():
                                return
                            s.flag[1] = True
                            break
                        time.sleep(0.001)
                    else:
                        s.flag[1] = True
                        continue
                    continue
                else:
                    if self.is_stopped():
                        s.flag[1] = False
                        return
                    time.sleep(0.001)

            # Критическая секция
            did_work = False
            try:
                if s.pending:
                    index = s.pending[0]
                    if 0 <= index < len(s.table):
                        value = s.table[index]["sum"]
                        is_even = (value % 2 == 0)
                        s.add_checker_result(is_even)
                        did_work = True
            finally:
                # Выход из критической секции
                s.turn = 0
                s.flag[1] = False

            # Если поток 2 что-то проверил, обновляем таблицу
            if did_work:
                self.app.ui_call(self.app.update_dekker_view)

            # Задержка: если работы не было, проверяем чаще; если была с учётом выбранной скорости
            if not self.controlled_sleep(0.7 if did_work else 0.3):
                break
