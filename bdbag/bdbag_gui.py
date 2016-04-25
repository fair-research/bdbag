import os
from Tkinter import *
from tkFileDialog import askopenfilename


class BDBagGUI(Frame):

    def __init__(self, master=None, **kw):
        Frame.__init__(self, master, **kw)
        self._bdbag_path = StringVar()
        self._bdbag_path_frame = Frame(self, height=2, bd=1, relief=FLAT)
        self._bdbag_path_frame.pack(side='top', fill=X, padx=5, pady=5)
        self._bag_path_label = Label(self._bdbag_path_frame, text='Bag Path:')
        self._bag_path_label.pack(side='left')
        self._bdbag_path_entry = Entry(self._bdbag_path_frame, width=85, textvariable=self._bdbag_path)
        self._bdbag_path_entry.pack(side='left')
        self._bdbag_path_browse = \
            Button(self._bdbag_path_frame, command=self._on__bdbag_path_browse_command, text='Browse')
        self._bdbag_path_browse.pack(side='right')
        self._Frame1 = Frame(self)
        self._Frame1.pack(side='top')

    def _on__bdbag_path_browse_command(self, event=None):
        Tk().withdraw()
        filename = askopenfilename()
        self._bdbag_path.set(os.path.normpath(filename))


def main():
    try:
        root = Tk()
        app = BDBagGUI(root)
        app.pack(expand='yes', fill='both')
        root.geometry('640x480+10+10')
        root.title('bdbag')
        root.mainloop()
    except Exception as e:
        sys.stderr.write(str(e))
        return 1


if __name__ == '__main__':
    sys.exit(main())
