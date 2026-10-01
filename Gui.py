import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import cv2
from PIL import Image, ImageTk

from puzzle import PuzzleBoard

GRID_COLOUR = "#d9d9d9"
SELECT_COLOUR = "#ff8c00"
TICK_COLOUR = "#1faa3b"
HINT_COLOUR = "#1e6bff"
PLACEHOLDER_SIZE = 420


class PuzzleApp(tk.Tk):

    # initializes the main application window and variables
    def __init__(self):
        super().__init__()
        self.title("Image Puzzle")
        self.resizable(False, False)

        self._board = None
        self._tile_w = 0           
        self._tile_h = 0
        self._selected = None       
        self._photos = {}           

        self._grid_var = tk.IntVar(value=3)
        self._moves_var = tk.StringVar()
        self._incorrect_var = tk.StringVar()
        self._hints_var = tk.StringVar()
        self._message_var = tk.StringVar(value="Choose a grid size, then load an image.")

        self._build_widgets()
        self._update_status()

    # creates and lays out all window widgets and canvases
    def _build_widgets(self):
        toolbar = ttk.Frame(self, padding=8)
        toolbar.pack(fill="x")

        ttk.Button(toolbar, text="Load Image", command=self.load_image).pack(side="left")

        ttk.Label(toolbar, text="   Grid size:").pack(side="left")
        for size in (3, 4, 5):
            ttk.Radiobutton(toolbar, text=f"{size} × {size}", value=size, variable=self._grid_var).pack(side="left", padx=2)

        self._solve_btn = ttk.Button(toolbar, text="Solve", command=self.solve)
        self._solve_btn.pack(side="right")
        self._hint_btn = ttk.Button(toolbar, text="Hint", command=self.hint)
        self._hint_btn.pack(side="right", padx=6)

        images = ttk.Frame(self, padding=(8, 0))
        images.pack()

        left = ttk.LabelFrame(images, text="Original (reference)")
        left.grid(row=0, column=0, padx=6, pady=4)
        self._original_canvas = tk.Canvas(left, width=PLACEHOLDER_SIZE, height=PLACEHOLDER_SIZE, bg="#f2f2f2", highlightthickness=0)
        self._original_canvas.pack()

        right = ttk.LabelFrame(images, text="Puzzle (click here)")
        right.grid(row=0, column=1, padx=6, pady=4)
        self._puzzle_canvas = tk.Canvas(right, width=PLACEHOLDER_SIZE, height=PLACEHOLDER_SIZE, bg="#f2f2f2", highlightthickness=0)
        self._puzzle_canvas.pack()

        for canvas in (self._original_canvas, self._puzzle_canvas):
            canvas.create_text(PLACEHOLDER_SIZE // 2, PLACEHOLDER_SIZE // 2, text="No image loaded", fill="#888888")

        self._puzzle_canvas.bind("<Button-1>", self._on_left_click)
        right_button = "<Button-2>" if sys.platform == "darwin" else "<Button-3>"
        self._puzzle_canvas.bind(right_button, self._on_right_click)

        status = ttk.Frame(self, padding=8)
        status.pack(fill="x")
        ttk.Label(status, textvariable=self._moves_var, width=12).pack(side="left")
        ttk.Label(status, textvariable=self._incorrect_var, width=18).pack(side="left")
        ttk.Label(status, textvariable=self._hints_var, width=14).pack(side="left")
        ttk.Label(status, textvariable=self._message_var, foreground="#444444").pack(side="left", padx=10)

    # opens file dialog to load image and create scrambled board
    def load_image(self):
        path = filedialog.askopenfilename(
            title="Choose an image",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp"), ("All files", "*.*")])
        if not path:
            return

        grid = self._grid_var.get()
        try:
            board = PuzzleBoard.from_script(path, grid)
        except (ValueError, OSError, cv2.error) as err:
            messagebox.showerror("Cannot load image", str(err))
            return

        full_w = board.tile_width * grid
        full_h = board.tile_height * grid
        avail_w = (self.winfo_screenwidth() - 120) // 2
        avail_h = self.winfo_screenheight() - 320
        scale = min(1.0, avail_w / full_w, avail_h / full_h)
        self._tile_w = max(1, int(board.tile_width * scale))
        self._tile_h = max(1, int(board.tile_height * scale))

        self._board = board
        self._selected = None
        for canvas in (self._original_canvas, self._puzzle_canvas):
            canvas.config(width=self._tile_w * grid, height=self._tile_h * grid)
        self._message_var.set("Left-click: select/swap  |  Right-click: rotate  |  Shift+click: flip")
        self._refresh()

    # triggers a hint request on the puzzle board
    def hint(self):
        if self._board is None:
            return
        if self._board.request_hint() is None:
            return
        self._refresh()

    # automatically solves the puzzle via the button
    def solve(self):
        if self._board is None or self._board.solved:
            return
        self._board.solve()
        self._selected = None
        self._message_var.set("Solved with the Solve button.")
        self._refresh()

    # converts canvas click coordinates into a tile grid index
    def _tile_at(self, event):
        if self._board is None:
            return None
        n = self._board.size
        if not (0 <= event.x < self._tile_w * n and 0 <= event.y < self._tile_h * n):
            return None
        return (event.y // self._tile_h) * n + (event.x // self._tile_w)

    # handles selection, swapping, and horizontal flipping via left-clicks
    def _on_left_click(self, event):
        position = self._tile_at(event)
        if position is None or self._board.solved:
            return

        if event.state & 0x0001:                 
            self._board.flip_horizontal(position)
        elif self._selected is None:              
            self._selected = position
        elif self._selected == position:           
            self._selected = None
        else:                                     
            self._board.swap(self._selected, position)
            self._selected = None
        self._after_action()

    # handles tile rotation via right-clicks
    def _on_right_click(self, event):
        position = self._tile_at(event)
        if position is None or self._board.solved:
            return
        self._board.rotate(position)
        self._after_action()

    # refreshes UI and displays victory popup if puzzle is completed
    def _after_action(self):
        self._refresh()
        if self._board.solved:
            self.update_idletasks()
            messagebox.showinfo(
                "Puzzle complete!",
                f"Well done! You solved it in {self._board.moves} moves.\n"
                "Load another image to keep playing.")

    # converts an OpenCV BGR image into a Tkinter PhotoImage object
    def _to_photo(self, bgr_image):
        n = self._board.size
        size = (self._tile_w * n, self._tile_h * n)
        if (bgr_image.shape[1], bgr_image.shape[0]) != size:
            bgr_image = cv2.resize(bgr_image, size, interpolation=cv2.INTER_AREA)
        rgb = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
        return ImageTk.PhotoImage(Image.fromarray(rgb))

    # calculates bounding box coordinates for a tile position
    def _cell(self, position):
        n = self._board.size
        row, col = divmod(position, n)
        x0, y0 = col * self._tile_w, row * self._tile_h
        return x0, y0, x0 + self._tile_w, y0 + self._tile_h

    # redraws both canvases and updates status labels
    def _refresh(self):
        self._draw_original()
        self._draw_puzzle()
        self._update_status()

    # renders the original reference image and hint marker
    def _draw_original(self):
        canvas = self._original_canvas
        canvas.delete("all")
        self._photos["original"] = self._to_photo(self._board.original_image)
        canvas.create_image(0, 0, anchor="nw", image=self._photos["original"])

        hint = self._board.hint
        if hint:
            self._draw_circle(canvas, hint[1])

    # renders the current puzzle state, selection box, grid lines, and ticks
    def _draw_puzzle(self):
        canvas = self._puzzle_canvas
        canvas.delete("all")
        self._photos["puzzle"] = self._to_photo(self._board.render())
        canvas.create_image(0, 0, anchor="nw", image=self._photos["puzzle"])

        n = self._board.size
        full_w, full_h = self._tile_w * n, self._tile_h * n
        for i in range(1, n):                       
            canvas.create_line(i * self._tile_w, 0, i * self._tile_w, full_h, fill=GRID_COLOUR)
            canvas.create_line(0, i * self._tile_h, full_w, i * self._tile_h, fill=GRID_COLOUR)

        for position in range(n * n):               
            if self._board.is_correct(position):
                self._draw_tick(canvas, position)

        if self._selected is not None:           
            x0, y0, x1, y1 = self._cell(self._selected)
            canvas.create_rectangle(x0 + 2, y0 + 2, x1 - 2, y1 - 2, outline=SELECT_COLOUR, width=4)

        hint = self._board.hint
        if hint:
            self._draw_circle(canvas, hint[0])

    # draws a green checkmark icon over correctly placed tiles
    def _draw_tick(self, canvas, position):
        x0, y0, x1, y1 = self._cell(position)
        canvas.create_oval(x1 - 30, y0 + 6, x1 - 6, y0 + 30, fill="white", outline=TICK_COLOUR, width=2)
        canvas.create_line(x1 - 25, y0 + 18, x1 - 20, y0 + 24, x1 - 11, y0 + 12, fill=TICK_COLOUR, width=3)

    # draws a blue highlight circle over a tile slot for hints
    def _draw_circle(self, canvas, position):
        x0, y0, x1, y1 = self._cell(position)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        r = min(self._tile_w, self._tile_h) * 0.3
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                           outline=HINT_COLOUR, width=4)

    # updates move counter, hint count, and button enable states
    def _update_status(self):
        board = self._board
        if board is None:
            self._moves_var.set("Moves: 0")
            self._incorrect_var.set("Tiles incorrect: -")
            self._hints_var.set("Hints left: -")
            self._hint_btn.state(["disabled"])
            self._solve_btn.state(["disabled"])
            return

        self._moves_var.set(f"Moves: {board.moves}")
        self._incorrect_var.set(f"Tiles incorrect: {board.incorrect_count}")
        self._hints_var.set(f"Hints left: {board.hints_left}")

        playing = not board.solved
        self._hint_btn.state(["!disabled"] if playing and board.hints_left > 0 else ["disabled"])
        self._solve_btn.state(["!disabled"] if playing else ["disabled"])
        if board.solved and board.moves > 0:
            self._message_var.set("Puzzle complete! Load another image to continue.")


if __name__ == "__main__":
    PuzzleApp().mainloop()
