"""
Главный файл программы (визуальная часть).

Здесь создаётся окно приложения на tkinter, две вкладки для двух заданий,
кнопки управления, таблица для 1 задания и визуализация для 2 задания.

Логика самих алгоритмов вынесена в отдельные файлы:
- dekker.py       -> алгоритм Деккера (задание 1)
- philosophers.py -> обедающие философы (задание 2)
- win_cs.py       -> критическая секция Windows для задания 2
"""

import tkinter as tk
from tkinter import ttk
import math

from dekker import DekkerShared, DekkerThread
from philosophers import (
    N_PHIL,
    THINKING,
    HUNGRY,
    EATING,
    STATE_NAMES,
    DiningState,
    PhilosopherThread,
)


class LabApp:
    """Класс приложения: хранит состояние и строит интерфейс."""

    def __init__(self, root):
        self.root = root
        self.root.title("Лабораторная работа №3 — Синхронизация процессов")
        self.root.geometry("1100x780")

        # Вкладки (Notebook): задание 1 и задание 2
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.tab1 = ttk.Frame(self.notebook)
        self.tab2 = ttk.Frame(self.notebook)
        self.notebook.add(self.tab1, text="Задание 1 — Алгоритм Деккера")
        self.notebook.add(self.tab2, text="Задание 2 — Обедающие философы")

        # --- Состояние задания 1 ---
        self.dekker_shared = None
        self.dekker_t0 = None
        self.dekker_t1 = None

        # --- Состояние задания 2 ---
        self.dining = None
        self.philosophers = [None] * N_PHIL

        # Создаём интерфейс вкладок
        self.build_task1()
        self.build_task2()

        # При закрытии окна корректно останавливаем потоки
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def ui_call(self, func, *args):
        """
        Безопасно вызвать обновление интерфейса из потока.
        Tkinter нужно обновлять из главного потока, поэтому используем root.after.
        """
        try:
            self.root.after(0, lambda: func(*args))
        except Exception:
            pass

    # =========================================================
    #                       ЗАДАНИЕ 1
    # =========================================================

    def build_task1(self):
        """Создание интерфейса для 1-го задания."""
        top = ttk.Frame(self.tab1)
        top.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        content = ttk.Frame(top)
        content.pack(fill=tk.BOTH, expand=True)

        # ----- Левая часть: таблица/буфер -----
        left = ttk.Frame(content)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        table_frame = ttk.LabelFrame(left, text="Таблица / буфер (результаты потоков отображаются сразу)")
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("idx", "sum", "even")
        self.dekker_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=18)
        self.dekker_tree.heading("idx", text="#")
        self.dekker_tree.heading("sum", text="Сумма (г+м+д+ч+мин+с) — поток 1")
        self.dekker_tree.heading("even", text="Чётное? (true/false) — поток 2")
        self.dekker_tree.column("idx", width=60, anchor=tk.CENTER)
        self.dekker_tree.column("sum", width=220, anchor=tk.CENTER)
        self.dekker_tree.column("even", width=220, anchor=tk.CENTER)
        self.dekker_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.dekker_tree.yview)
        self.dekker_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # ----- Правая часть: управление потоками -----
        controls = ttk.LabelFrame(content, text="Управление потоками")
        controls.pack(side=tk.RIGHT, fill=tk.Y)

        # Поток 1
        f1 = ttk.LabelFrame(controls, text="Поток 1 (сумма даты/времени)")
        f1.pack(fill=tk.X, padx=6, pady=6)

        ttk.Label(f1, text="Скорость (задержка, с):").pack(anchor=tk.W, padx=4, pady=(4, 0))
        self.t1_speed = tk.DoubleVar(value=1.0)
        ttk.Scale(f1, from_=0.1, to=3.0, variable=self.t1_speed, orient=tk.HORIZONTAL, length=220,
                  command=lambda v: self.set_dekker_speed(0)).pack(fill=tk.X, padx=4)
        self.t1_speed_lbl = ttk.Label(f1, text="1.00")
        self.t1_speed_lbl.pack(anchor=tk.W, padx=4)

        b1 = ttk.Frame(f1)
        b1.pack(fill=tk.X, padx=4, pady=4)
        ttk.Button(b1, text="Запуск", command=lambda: self.start_dekker_thread(0)).pack(side=tk.LEFT, padx=2)
        ttk.Button(b1, text="Пауза", command=lambda: self.pause_dekker_thread(0)).pack(side=tk.LEFT, padx=2)

        # Поток 2
        f2 = ttk.LabelFrame(controls, text="Поток 2 (проверка чётности)")
        f2.pack(fill=tk.X, padx=6, pady=6)

        ttk.Label(f2, text="Скорость (задержка, с):").pack(anchor=tk.W, padx=4, pady=(4, 0))
        self.t2_speed = tk.DoubleVar(value=1.0)
        ttk.Scale(f2, from_=0.1, to=3.0, variable=self.t2_speed, orient=tk.HORIZONTAL, length=220,
                  command=lambda v: self.set_dekker_speed(1)).pack(fill=tk.X, padx=4)
        self.t2_speed_lbl = ttk.Label(f2, text="1.00")
        self.t2_speed_lbl.pack(anchor=tk.W, padx=4)

        b2 = ttk.Frame(f2)
        b2.pack(fill=tk.X, padx=4, pady=4)
        ttk.Button(b2, text="Запуск", command=lambda: self.start_dekker_thread(1)).pack(side=tk.LEFT, padx=2)
        ttk.Button(b2, text="Пауза", command=lambda: self.pause_dekker_thread(1)).pack(side=tk.LEFT, padx=2)

        # Общие кнопки
        f3 = ttk.LabelFrame(controls, text="Общее")
        f3.pack(fill=tk.X, padx=6, pady=6)
        ttk.Button(f3, text="Запуск обоих", command=self.start_dekker_both).pack(fill=tk.X, padx=4, pady=2)
        ttk.Button(f3, text="Пауза обоих", command=self.pause_dekker_both).pack(fill=tk.X, padx=4, pady=2)
        ttk.Button(f3, text="Стоп обоих", command=self.stop_dekker_both).pack(fill=tk.X, padx=4, pady=2)
        ttk.Button(f3, text="Очистить таблицу", command=self.clear_dekker_table).pack(fill=tk.X, padx=4, pady=(8, 4))
        ttk.Button(f3, text="Выход", command=self.on_close).pack(fill=tk.X, padx=4, pady=(8, 4))

        # Текст задания (внизу вкладки)
        task_frame = ttk.LabelFrame(self.tab1, text="Задание 1")
        task_frame.pack(fill=tk.X, pady=(8, 0))
        task_text = (
            "1. С помощью алгоритма Деккера организовать работу параллельных вычислительных потоков. "
            "Первый поток подсчитывает сумму сегодняшней даты и времени (г+м+д+ч+мин+с) и записывает в таблицу. "
            "Второй поток проверяет, четное ли число записано в таблице, если да – устанавливает соответствующее "
            "поле таблицы в true, если нет – в false."
        )
        txt = tk.Text(task_frame, height=4, wrap=tk.WORD)
        txt.insert("1.0", task_text)
        txt.configure(state=tk.DISABLED)
        txt.pack(fill=tk.X, padx=4, pady=4)

    def init_dekker(self):
        """Создаём общие данные для задания 1, если они ещё не созданы."""
        if self.dekker_shared is None:
            self.dekker_shared = DekkerShared()

    def set_dekker_speed(self, idx):
        """Обновление скорости (задержки) для выбранного потока."""
        if idx == 0:
            value = self.t1_speed.get()
            self.t1_speed_lbl.config(text=f"{value:.2f}")
            if self.dekker_t0:
                self.dekker_t0.speed_delay = value
        else:
            value = self.t2_speed.get()
            self.t2_speed_lbl.config(text=f"{value:.2f}")
            if self.dekker_t1:
                self.dekker_t1.speed_delay = value

    def start_dekker_thread(self, idx):
        """Запуск (или продолжение после паузы) потока 0 или 1."""
        self.init_dekker()

        if idx == 0:
            if self.dekker_t0 and self.dekker_t0.is_alive():
                self.dekker_t0.resume()
                self.update_dekker_view()
                return
            self.dekker_t0 = DekkerThread(0, self.dekker_shared, self)
            self.dekker_t0.speed_delay = self.t1_speed.get()
            self.dekker_t0.start()
        else:
            if self.dekker_t1 and self.dekker_t1.is_alive():
                self.dekker_t1.resume()
                self.update_dekker_view()
                return
            self.dekker_t1 = DekkerThread(1, self.dekker_shared, self)
            self.dekker_t1.speed_delay = self.t2_speed.get()
            self.dekker_t1.start()

        self.update_dekker_view()

    def pause_dekker_thread(self, idx):
        """Пауза потока 0 или 1."""
        thread = self.dekker_t0 if idx == 0 else self.dekker_t1
        if thread and thread.is_alive():
            thread.pause()
        self.update_dekker_view()

    def start_dekker_both(self):
        self.start_dekker_thread(0)
        self.start_dekker_thread(1)

    def pause_dekker_both(self):
        self.pause_dekker_thread(0)
        self.pause_dekker_thread(1)

    def stop_dekker_both(self):
        """Полная остановка обоих потоков (общая кнопка Стоп)."""
        if self.dekker_t0:
            self.dekker_t0.stop()
            self.dekker_t0 = None
        if self.dekker_t1:
            self.dekker_t1.stop()
            self.dekker_t1 = None
        self.update_dekker_view()

    def clear_dekker_table(self):
        """Очистить таблицу результатов."""
        if self.dekker_shared:
            self.dekker_shared.table.clear()
            self.dekker_shared.pending = []
            self.dekker_shared.next_id = 1
        self.update_dekker_view()

    def update_dekker_view(self):
        """Обновить содержимое таблицы на экране."""
        # Очищаем таблицу в интерфейсе
        for item in self.dekker_tree.get_children():
            self.dekker_tree.delete(item)

        if not self.dekker_shared:
            return

        # Заполняем таблицу актуальными данными
        for row in self.dekker_shared.table:
            if row["even"] is None:
                even_text = ""
            else:
                even_text = "true" if row["even"] else "false"
            self.dekker_tree.insert("", tk.END, values=(row.get("id", ""), row["sum"], even_text))

        # Прокручиваем к последней строке, чтобы было видно новые результаты
        children = self.dekker_tree.get_children()
        if children:
            self.dekker_tree.see(children[-1])

    # =========================================================
    #                       ЗАДАНИЕ 2
    # =========================================================

    def build_task2(self):
        """Создание интерфейса для 2-го задания."""
        top = ttk.Frame(self.tab2)
        top.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        controls = ttk.LabelFrame(top, text="Управление философами")
        controls.pack(fill=tk.X, pady=(0, 8))

        # Общие кнопки
        g = ttk.Frame(controls)
        g.pack(fill=tk.X, padx=5, pady=3)
        ttk.Button(g, text="Запуск всех", command=self.start_all_philosophers).pack(side=tk.LEFT, padx=2)
        ttk.Button(g, text="Пауза всех", command=self.pause_all_philosophers).pack(side=tk.LEFT, padx=2)
        ttk.Button(g, text="Стоп всех", command=self.stop_all_philosophers).pack(side=tk.LEFT, padx=2)
        ttk.Button(g, text="Выход", command=self.on_close).pack(side=tk.LEFT, padx=(10, 2))
        ttk.Label(g, text="Время размышления задаётся для каждого философа отдельно; время еды фиксировано.").pack(
            side=tk.LEFT, padx=10
        )

        # Индивидуальные настройки философов
        self.phil_controls_frame = ttk.Frame(controls)
        self.phil_controls_frame.pack(fill=tk.X, padx=5, pady=3)

        self.phil_speed_vars = []
        self.phil_speed_labels = []

        for i in range(N_PHIL):
            row = ttk.Frame(self.phil_controls_frame)
            row.pack(fill=tk.X, pady=1)

            ttk.Label(row, text=f"Философ {i} (время размышления, с):").pack(side=tk.LEFT)

            var = tk.DoubleVar(value=1.0)
            self.phil_speed_vars.append(var)
            ttk.Scale(row, from_=0.1, to=10.0, variable=var, orient=tk.HORIZONTAL, length=150,
                      command=lambda v, idx=i: self.set_phil_speed(idx)).pack(side=tk.LEFT, padx=4)

            lbl = ttk.Label(row, text="1.00с")
            lbl.pack(side=tk.LEFT)
            self.phil_speed_labels.append(lbl)

            ttk.Button(row, text="Запуск", command=lambda idx=i: self.start_philosopher(idx)).pack(side=tk.LEFT, padx=2)
            ttk.Button(row, text="Пауза", command=lambda idx=i: self.pause_philosopher(idx)).pack(side=tk.LEFT, padx=2)

        # Основная область: слева визуализация, справа текст задания
        mid = ttk.Frame(top)
        mid.pack(fill=tk.BOTH, expand=True)

        vis_frame = ttk.LabelFrame(mid, text="Визуализация: философы, вилки, состояния, семафоры")
        vis_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        self.canvas = tk.Canvas(vis_frame, width=520, height=520, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        right = ttk.Frame(mid)
        right.pack(side=tk.RIGHT, fill=tk.Y)

        task_frame = ttk.LabelFrame(right, text="Задание 2")
        task_frame.pack(fill=tk.BOTH, expand=True)
        task_text = (
            "2. Задачу об обедающих философах решить с помощью системных функций EnterCriticalSection() и "
            "LeaveCriticalSection().\n"
        )
        txt = tk.Text(task_frame, width=36, wrap=tk.WORD)
        txt.insert("1.0", task_text)
        txt.configure(state=tk.DISABLED)
        txt.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Первая отрисовка
        self.update_philosophers_view()

    def init_dining(self):
        """Создаём общее состояние задачи 2, если оно ещё не создано."""
        if self.dining is None:
            self.dining = DiningState()
            self.philosophers = [None] * N_PHIL

    def set_phil_speed(self, idx):
        """Изменить время размышления философа idx."""
        value = self.phil_speed_vars[idx].get()
        self.phil_speed_labels[idx].config(text=f"{value:.2f}с")
        if self.philosophers[idx]:
            self.philosophers[idx].speed_delay = value

    def start_philosopher(self, idx):
        """Запуск философа idx (или продолжение после паузы)."""
        self.init_dining()

        if self.philosophers[idx] and self.philosophers[idx].is_alive():
            self.philosophers[idx].resume()
            self.update_philosophers_view()
            return

        thread = PhilosopherThread(idx, self.dining, self)
        thread.speed_delay = self.phil_speed_vars[idx].get()
        self.philosophers[idx] = thread
        thread.start()
        self.update_philosophers_view()

    def pause_philosopher(self, idx):
        """Пауза философа idx."""
        if self.philosophers[idx] and self.philosophers[idx].is_alive():
            self.philosophers[idx].pause()
        self.update_philosophers_view()

    def start_all_philosophers(self):
        for i in range(N_PHIL):
            self.start_philosopher(i)

    def pause_all_philosophers(self):
        for i in range(N_PHIL):
            self.pause_philosopher(i)

    def stop_all_philosophers(self):
        """Общая кнопка Стоп: останавливаем всех и сбрасываем состояние."""
        for i in range(N_PHIL):
            if self.philosophers[i]:
                self.philosophers[i].stop()
            self.philosophers[i] = None

        self.dining = DiningState()
        self.update_philosophers_view()

    def update_philosophers_view(self):
        """Обновить визуализацию философов."""
        if self.dining:
            d = self.dining
            # Читаем состояние под mutex, чтобы данные были согласованными
            d.down_mutex()
            try:
                snapshot = {
                    "state": list(d.state),
                    "sem": list(d.sem_view),
                    "forks": list(d.forks),
                }
            finally:
                d.up_mutex()
            self.draw_dining(snapshot)
        else:
            # Отрисовка по умолчанию (все думают, все вилки на столе)
            self.draw_dining({
                "state": [THINKING] * N_PHIL,
                "sem": [0] * N_PHIL,
                "forks": [True] * N_PHIL,
            })

    def draw_dining(self, snapshot):
        """Нарисовать стол, философов, вилки, состояния и семафоры."""
        c = self.canvas
        c.delete("all")

        # Размеры холста и основные параметры рисунка
        w = int(c.winfo_width() or 520)
        h = int(c.winfo_height() or 520)
        cx, cy = w // 2, h // 2
        table_r = min(w, h) // 5
        phil_r = min(w, h) // 11
        fork_len = min(w, h) // 10

        # Стол
        c.create_oval(cx - table_r, cy - table_r, cx + table_r, cy + table_r,
                      fill="#f5deb3", outline="#8b5a2b", width=2)
        c.create_text(cx, cy, text="Стол", font=("Arial", 10, "bold"))

        # Цвета состояний
        state_colors = {
            THINKING: "#87ceeb",  # думает
            HUNGRY: "#ffd700",    # голоден
            EATING: "#90ee90",    # ест
        }

        # Позиции философов вокруг стола
        phil_pos = []
        for i in range(N_PHIL):
            angle = -math.pi / 2 + i * 2 * math.pi / N_PHIL
            px = cx + int((table_r + phil_r + 20) * math.cos(angle))
            py = cy + int((table_r + phil_r + 20) * math.sin(angle))
            phil_pos.append((px, py))

        # Позиции вилок между философами (вилка i между i и i+1)
        fork_pos = []
        for i in range(N_PHIL):
            angle = -math.pi / 2 + (i + 0.5) * 2 * math.pi / N_PHIL
            fx = cx + int((table_r - 5) * math.cos(angle))
            fy = cy + int((table_r - 5) * math.sin(angle))
            fork_pos.append((fx, fy, angle))

        # Рисуем вилки
        for i, (fx, fy, angle) in enumerate(fork_pos):
            is_free = snapshot["forks"][i]
            color = "#444444" if is_free else "#cc0000"
            x2 = fx + int(fork_len * 0.7 * math.cos(angle))
            y2 = fy + int(fork_len * 0.7 * math.sin(angle))
            c.create_line(fx, fy, x2, y2, width=5, fill=color)
            c.create_oval(fx - 4, fy - 4, fx + 4, fy + 4, fill=color, outline=color)
            c.create_text(fx + int(18 * math.cos(angle)), fy + int(18 * math.sin(angle)),
                          text=f"V{i}", font=("Arial", 8))

        # Рисуем философов
        for i, (px, py) in enumerate(phil_pos):
            st = snapshot["state"][i]
            st_name = STATE_NAMES.get(st, str(st))
            color = state_colors.get(st, "#ddd")

            c.create_oval(px - phil_r, py - phil_r, px + phil_r, py + phil_r,
                          fill=color, outline="black", width=2)
            c.create_text(px, py - 8, text=f"P{i}", font=("Arial", 10, "bold"))
            c.create_text(px, py + 8, text=st_name, font=("Arial", 8))
            c.create_text(px, py + phil_r + 12, text=f"sem={snapshot['sem'][i]}", font=("Arial", 8))

        # Легенда
        ly = 15
        c.create_text(70, ly, text="Легенда:", anchor=tk.W, font=("Arial", 9, "bold"))
        for label, col in [("думает", state_colors[THINKING]),
                           ("голоден", state_colors[HUNGRY]),
                           ("ест", state_colors[EATING])]:
            ly += 18
            c.create_rectangle(10, ly - 7, 25, ly + 7, fill=col, outline="black")
            c.create_text(30, ly, text=label, anchor=tk.W, font=("Arial", 9))

        ly += 18
        c.create_line(10, ly, 25, ly, fill="#444", width=4)
        c.create_text(30, ly, text="вилка свободна", anchor=tk.W, font=("Arial", 9))

        ly += 18
        c.create_line(10, ly, 25, ly, fill="#cc0000", width=4)
        c.create_text(30, ly, text="вилка занята", anchor=tk.W, font=("Arial", 9))

    # =========================================================
    #                 Завершение программы
    # =========================================================

    def on_close(self):
        """Корректно остановить потоки и закрыть окно."""
        try:
            self.stop_dekker_both()
        except Exception:
            pass
        try:
            self.stop_all_philosophers()
        except Exception:
            pass
        self.root.destroy()


def main():
    root = tk.Tk()

    # Пытаемся выбрать более аккуратную тему оформления (если доступна)
    try:
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
        elif "clam" in style.theme_names():
            style.theme_use("clam")
    except Exception:
        pass

    app = LabApp(root)

    # При изменении размера окна перерисовываем визуализацию задания 2
    def on_resize(event):
        if app.dining:
            app.update_philosophers_view()
        else:
            app.draw_dining({
                "state": [THINKING] * N_PHIL,
                "sem": [0] * N_PHIL,
                "forks": [True] * N_PHIL,
            })

    app.canvas.bind("<Configure>", on_resize)

    root.mainloop()


if __name__ == "__main__":
    main()
