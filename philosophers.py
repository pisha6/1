"""
Логика 2-го задания: задача об обедающих философах.

Реализация сделана по структуре классического алгоритма с семафорами:
- N, LEFT(i), RIGHT(i)
- state[N] (THINKING, HUNGRY, EATING)
- mutex (взаимное исключение при проверке/изменении состояний)
- s[N] (по одному семафору на философа)
- функции/методы test, take_forks, put_forks, цикл философа

По условию лабораторной работы для взаимного исключения используются
системные функции Windows EnterCriticalSection() / LeaveCriticalSection().
Поэтому mutex реализован через WinAPI (см. win_cs.py).
"""

import threading
import time

from win_cs import WinCriticalSection

N = 5          # количество философов
N_PHIL = N     # то же самое имя для удобства использования в интерфейсе

THINKING = 0   # философ думает
HUNGRY = 1     # философ голоден
EATING = 2     # философ ест

# Фиксированное время приёма пищи для всех философов (в секундах)
EAT_TIME = 1.5

# Названия состояний для отображения в интерфейсе
STATE_NAMES = {
    THINKING: "думает",
    HUNGRY: "голоден",
    EATING: "ест",
}


def LEFT(i):
    """Номер левого соседа для философа i."""
    return (i - 1) % N


def RIGHT(i):
    """Номер правого соседа для философа i."""
    return (i + 1) % N


class DiningState:
    """Общее состояние задачи: философы, вилки, mutex и семафоры s[N]."""

    def __init__(self):
        # Массив состояний философов
        self.state = [THINKING] * N

        # mutex реализованный через Enter/LeaveCriticalSection
        self.mutex = WinCriticalSection()

        # По одному семафору на философа (s[i])
        # Начальное значение 0: философ блокируется на down(s[i]), если вилки не удалось взять
        self.s = [threading.Semaphore(0) for _ in range(N)]

        # Отдельное поле для визуализации "семафора" в интерфейсе
        # 0 - философ ждёт/не имеет разрешения, 1 - получил разрешение есть
        self.sem_view = [0] * N

        # Флаг остановки всей симуляции
        self.stop = False

    @property
    def forks(self):
        """
        Вычисляем состояние вилок для визуализации.
        Вилка i находится между философом i и (i+1)%N.
        Она занята, если ест философ i или философ (i+1)%N.
        """
        forks = [True] * N  # True = на столе, False = занята
        for i in range(N):
            if self.state[i] == EATING or self.state[RIGHT(i)] == EATING:
                forks[i] = False
        return forks

    # Операции с mutex (критическая секция Windows)

    def down_mutex(self):
        # Вход в критическую секцию
        self.mutex.enter()

    def up_mutex(self):
        # Выход из критической секции
        self.mutex.leave()

    # Операции с семафорами философов s[i]

    def up_s(self, i):
        """Аналог up(s[i]): разрешаем философу i начать есть."""
        self.sem_view[i] = 1
        self.s[i].release()

    def down_s_wait(self, i, thread):
        """
        Аналог down(s[i]), но с ожиданием "маленькими шагами".
        Это нужно, чтобы поток корректно реагировал на паузу и кнопку Стоп.
        """
        while not thread.is_stopped() and not self.stop:
            # Если поставили паузу — ждём снятия паузы
            if not thread.wait_if_paused():
                return False

            # Пытаемся захватить семафор с таймаутом
            if self.s[i].acquire(timeout=0.05):
                self.sem_view[i] = 0
                return True

        return False

    # Основные функции алгоритма

    def test(self, i):
        """
        Проверка: может ли философ i начать есть?
        Условие как в псевдокоде:
        если философ голоден и соседи не едят -> переводим его в EATING и делаем up(s[i]).
        """
        if self.state[i] == HUNGRY and self.state[LEFT(i)] != EATING and self.state[RIGHT(i)] != EATING:
            self.state[i] = EATING
            self.up_s(i)

    def take_forks(self, i, thread):
        """Философ i пытается взять вилки (take_forks)."""
        self.down_mutex()
        try:
            self.state[i] = HUNGRY   # философ проголодался
            self.sem_view[i] = 0
            self.test(i)             # пробуем взять обе вилки сразу
        finally:
            self.up_mutex()

        # Если вилки взять не удалось, test() не сделал up(s[i]), и здесь поток будет ждать
        return self.down_s_wait(i, thread)

    def put_forks(self, i):
        """Философ i кладёт вилки (put_forks)."""
        self.down_mutex()
        try:
            self.state[i] = THINKING  # закончил есть
            self.sem_view[i] = 0
            self.test(LEFT(i))        # проверить левого соседа
            self.test(RIGHT(i))       # проверить правого соседа
        finally:
            self.up_mutex()


class PhilosopherThread(threading.Thread):
    """Поток одного философа."""

    def __init__(self, i, dining: DiningState, app):
        super().__init__(daemon=True)
        self.i = i
        self.dining = dining
        self.app = app

        # Индивидуальное время размышления (задаётся ползунком в интерфейсе)
        self.speed_delay = 1.0

        # Управление паузой/остановкой
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._stop_event = threading.Event()

    # Управление потоком 

    def pause(self):
        self._pause_event.clear()

    def resume(self):
        self._pause_event.set()

    def stop(self):
        self._stop_event.set()
        self._pause_event.set()

    def is_stopped(self):
        return self._stop_event.is_set()

    def wait_if_paused(self):
        while not self.is_stopped():
            if self._pause_event.is_set():
                return True
            time.sleep(0.05)
        return False

    def sleep_with_control(self, seconds):
        """
        Ожидание заданного времени маленькими шагами,
        чтобы корректно работали пауза и остановка.
        """
        end_time = time.time() + max(0.01, seconds)
        while time.time() < end_time:
            if self.is_stopped() or self.dining.stop:
                return False
            if not self._pause_event.is_set():
                if not self.wait_if_paused():
                    return False
            time.sleep(0.02)
        return not (self.is_stopped() or self.dining.stop)

    # Действия философа

    def think(self):
        """Философ думает (время индивидуальное)."""
        return self.sleep_with_control(self.speed_delay)

    def eat(self):
        """Философ ест (время фиксированное для всех)."""
        return self.sleep_with_control(EAT_TIME)

    # Основной цикл философа 

    def run(self):
        i = self.i
        d = self.dining

        # Цикл: think -> take_forks -> eat -> put_forks
        while not self.is_stopped() and not d.stop:
            if not self.wait_if_paused():
                break

            # 1) Думает
            d.down_mutex()
            try:
                d.state[i] = THINKING
                d.sem_view[i] = 0
            finally:
                d.up_mutex()
            self.app.ui_call(self.app.update_philosophers_view)

            if not self.think():
                break

            # 2) Пытается взять вилки (внутри выставится HUNGRY и, возможно, ожидание на s[i])
            self.app.ui_call(self.app.update_philosophers_view)
            if not d.take_forks(i, self):
                break
            self.app.ui_call(self.app.update_philosophers_view)

            # 3) Ест
            if not self.eat():
                # Если остановили во время еды — корректно кладём вилки
                d.put_forks(i)
                self.app.ui_call(self.app.update_philosophers_view)
                break

            # 4) Кладёт вилки
            d.put_forks(i)
            self.app.ui_call(self.app.update_philosophers_view)
