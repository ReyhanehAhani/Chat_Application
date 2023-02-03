try:
    import collections
    import io
    import random
    import socket
    import threading
    import tkinter
    import tkinter.ttk as ttk
    import webbrowser
    from datetime import datetime
    from pathlib import Path
    from tkinter import filedialog, messagebox
    from PIL import Image, ImageTk
except (ModuleNotFoundError, ImportError) as e:
    print(e)
    messagebox.showerror('Required libraries not found', 'Please install the required libraries: pillow for python (PIL)')
    exit(1)


CHAT_PORT = random.randint(5000, 10000)
SPLITTER = "^^^^"
ICON_FILE_PATH = './assets/icon.png'
BACKGROUND_FILE_PATH = './assets/background.png'

def generateFileName():
    return f'./Downloads/{datetime.today().strftime("%Y-%m-%d-%H-%M-%S")}.png'

def setIcon(root: tkinter.Tk):
    if not Path(ICON_FILE_PATH).exists():
        messagebox.showerror('Required icon not found', f'Required icon `{ICON_FILE_PATH}` not found')
        exit(1)
    
    root.iconphoto(False, tkinter.PhotoImage(file=ICON_FILE_PATH))


class Message():
    def __init__(self, message, messageType):
        self.message = message
        self.messageType = messageType

    @classmethod
    def from_byte(cls, msg):
        msg = msg.decode().split('SPLITTER')
        return Message(msg[0], msg[1])

    def to_byte(self):
        return f"{self.message}{SPLITTER}{self.messageType}".encode()


def ImageMessage(data):
    b_data = data
    b_data += SPLITTER.encode()
    b_data += b'IMG'
    return b_data


class OffThreadClientWaiter(threading.Thread):
    def __init__(self, targetWindow: tkinter.Tk, targetSocket: socket.socket):
        super().__init__()
        self.targetWindow = targetWindow
        self.targetSocket = targetSocket

    def run(self):
        try:
            self.targetSocket.listen(1)
            connection, addr = self.targetSocket.accept()
            self.targetWindow.socket_connection = connection
            self.targetWindow.addr_connection = addr
            self.targetWindow.event_generate('<<onConnect>>', when='tail')
        except ConnectionError as e:
            self.targetWindow.event_generate('<<onError>>', when='tail')


class OffThreadMsgReciver(threading.Thread):
    def __init__(self, targetWindow: tkinter.Tk, targetSocket: socket.socket):
        super().__init__()
        self.targetWindow = targetWindow
        self.targetSocket = targetSocket
        self.checkForMsgs = True

    def run(self):
        while self.checkForMsgs:
            BUFF_SIZE = 4096
            data = b''

            while self.checkForMsgs:
                try:
                    recived = self.targetSocket.recv(BUFF_SIZE)
                    data += recived
                    if len(recived) < BUFF_SIZE:
                        break
                except ConnectionError as e:
                    self.checkForMsgs = False
                    self.targetWindow.event_generate(
                        '<<onError>>', when='tail')

            if (data[-3:] == b'STR') or (data[-3:] == b'COM'):
                if data[-3:] == b'STR':
                    self.targetWindow.receiveText(data[:-7].decode())
                else:
                    self.targetWindow.receiveCommand(data[:-7].decode())
            elif (data[-3:] == b'IMG'):
                self.targetWindow.download(data[:-7])


class OffThreadImageSend(threading.Thread):
    def __init__(self, targetWindow: tkinter.Tk, targetSocket: socket.socket, data):
        super().__init__()
        self.targetWindow = targetWindow
        self.targetSocket = targetSocket
        self.data = data

    def run(self):
        self.byte_arr = io.BytesIO()
        self.data.save(self.byte_arr, format='PNG')
        self.byte_arr = self.byte_arr.getvalue()

        try:
            self.targetSocket.send(ImageMessage(self.byte_arr))
        except ConnectionError as e:
            self.targetWindow.event_generate('<<onError>>', when='tail')


class ScrollableFrame(tkinter.Frame):
    def __init__(self, parent, *args, **kw):
        ttk.Frame.__init__(self, parent, *args, **kw)

        # create a canvas object and a vertical scrollbar for scrolling it
        vscrollbar = ttk.Scrollbar(self, orient=tkinter.VERTICAL)
        vscrollbar.pack(fill=tkinter.Y, side=tkinter.RIGHT,
                        expand=tkinter.FALSE)

        canvas = tkinter.Canvas(self, bd=0, highlightthickness=0,
                                yscrollcommand=vscrollbar.set)

        
        canvas.pack(side=tkinter.LEFT, fill=tkinter.BOTH, expand=tkinter.TRUE)
        vscrollbar.config(command=canvas.yview)

        # reset the view
        canvas.xview_moveto(0)
        canvas.yview_moveto(0)

        # create a frame inside the canvas which will be scrolled with it
        self.interior = interior = tkinter.Frame(canvas)
        interior_id = canvas.create_window(0, 0, window=interior,
                                           anchor=tkinter.NW)

        # track changes to the canvas and frame width and sync them,
        # also updating the scrollbar
        def _configure_interior(event):
            # update the scrollbars to match the size of the inner frame
            size = (interior.winfo_reqwidth(), interior.winfo_reqheight())
            canvas.config(scrollregion="0 0 %s %s" % size)
        
            if interior.winfo_reqwidth() != canvas.winfo_width():
                # update the canvas's width to fit the inner frame
                canvas.config(width=interior.winfo_reqwidth())

        interior.bind('<Configure>', _configure_interior)

        def _configure_canvas(event):
            if interior.winfo_reqwidth() != canvas.winfo_width():
                # update the inner frame's width to fill the canvas
                canvas.itemconfigure(interior_id, width=canvas.winfo_width())
        canvas.bind('<Configure>', _configure_canvas)


class ChatScreen(tkinter.Tk):
    def __init__(self, chatType: str, connction: socket.socket):
        super().__init__()
        setIcon(self)
        self.geometry('400x500')
        self.title("Chat app: Chat screen")

        self.Msgs = ScrollableFrame(self)
        self.Msgs.grid(row=0, column=0, columnspan=2, rowspan=2, sticky="NSEW")

        self.Msgs.column_counter = 1
        self.Msgs.interior.grid_columnconfigure(tuple(range(2)), weight=1)

        self.msgText = ttk.Entry(self)
        self.msgText.grid(row=2, column=0, columnspan=2, sticky="SNEW")

        self.uploadButton = ttk.Button(
            self, text='Upload message', command=self.upload)
        self.uploadButton.grid(row=3, column=1, sticky="NSEW")

        self.sendButton = ttk.Button(
            self, text='Send message', command=self.send)
        self.sendButton.grid(row=3, column=0, sticky="NSEW")

        self.grid_rowconfigure(tuple(range(4)), weight=1)
        self.grid_columnconfigure(tuple(range(2)), weight=1)

        self.chatType = chatType
        self.connction = connction

        self.recevier = OffThreadMsgReciver(self, self.connction)
        self.recevier.daemon = True
        self.recevier.start()

        def on_error_func(x): return self.onErrorThread()
        self.bind('<<onError>>', on_error_func)

        self.msgs_imgs = collections.deque()

    def send(self):
        msg = self.msgText.get()

        if msg:
            self.msgText.delete(0, 'end')
            ttk.Label(self.Msgs.interior, text=msg, background="#9cf0ff", wraplength=500, justify="left").grid(
                row=self.Msgs.column_counter * 2, column=1, sticky="NSEW", ipady=5, ipadx=5, pady=5, padx=5)
            self.Msgs.column_counter += 1

            try:
                self.connction.send(Message(msg, 'STR').to_byte())
            except ConnectionError as e:
                self.onConnectionError(e)

    def upload(self):
        filename = filedialog.askopenfilename(title="Please select a file to upload", filetypes=(
            ('PNG files', '*.png'), ('JPG files', '*.jpg')))

        img = Image.open(filename)

        sender = OffThreadImageSend(self, self.connction, img.copy())
        sender.daemon = True
        sender.start()

        img.thumbnail((250, 125))
        tk_img = ImageTk.PhotoImage(img)

        l1 = ttk.Label(self.Msgs.interior, image=tk_img)
        l1.bind('<Button-1>', lambda e: webbrowser.open(f'file://{filename}'))
        l1.grid(
            row=self.Msgs.column_counter * 2, column=1, sticky="NSEW", ipady=5, ipadx=5, pady=5, padx=5)

        self.Msgs.column_counter += 1
        self.msgs_imgs.append(tk_img)

    def download(self, data):
        fname = generateFileName()

        with open(fname, 'wb') as f:
            f.write(data)

        img = Image.open(fname)
        img.thumbnail((250, 125))
        tk_img = ImageTk.PhotoImage(img)

        l1 = ttk.Label(self.Msgs.interior, image=tk_img)
        l1.bind('<Button-1>', lambda e: webbrowser.open(f'file://{fname}'))
        l1.grid(
            row=self.Msgs.column_counter * 2 - 1, column=0, sticky="NSEW", ipady=5, ipadx=5, pady=5, padx=5)

        self.Msgs.column_counter += 1
        self.msgs_imgs.append(tk_img)

    def receiveText(self, msg):
        if msg:
            ttk.Label(self.Msgs.interior, text=msg, background="#fcba03", wraplength=500, justify="left").grid(
                row=self.Msgs.column_counter * 2 - 1, column=0, sticky="NSEW", ipady=5, ipadx=5, pady=5, padx=5)
            self.Msgs.column_counter += 1

    def receiveCommand(self, com):
        if com == '/EXIT':
            self.recevier.checkForMsgs = False
            self.connction.close()
            self.destroy()

    def onConnectionError(self, e):
        messagebox.showerror('Error in communication',
                             'Error in communication, couldn\'t send messages, please try again.')

    def onErrorThread(self):
        messagebox.showerror('Error in communication',
                             'Error in communication, couldn\'t receive messages')
        self.connction.close()
        self.destroy()


class ClientConnectScreen(tkinter.Tk):
    def __init__(self):
        super().__init__()
        setIcon(self)
        self.geometry('350x150')
        self.title("Chat app: Waiting to join to a server")
        self.resizable(False, False)

        self.waitMessage = ttk.Label(self, text='Join information: ')
        self.waitMessage.grid(pady=10, row=0, column=1)

        self.IPtextBox = ttk.Entry(self)
        self.IPtextBox.grid(pady=10, padx=10, row=1, column=1)

        self.IPLabel = ttk.Label(self, text='IP address: ')
        self.IPLabel.grid(pady=10, padx=10, row=1, column=0)

        self.PortTextBox = ttk.Entry(self)
        self.PortTextBox.grid(pady=10, padx=10, row=2, column=1)

        self.PortLabel = ttk.Label(self, text='Port: ')
        self.PortLabel.grid(pady=10, padx=10, row=2, column=0)

        self.joinButton = ttk.Button(self, text='Join', command=self.connectTo)
        self.joinButton.grid(pady=10, padx=10, row=1, column=2)

    def connectTo(self):
        ip = self.IPtextBox.get()
        port = self.PortTextBox.get()

        if ip and port:
            try:
                Socket = socket.socket()
                Socket.connect((ip, int(port)))
                self.destroy()
                win = ChatScreen('J', Socket)
                win.mainloop()
            except:
                messagebox.showerror('Error in connection',
                                     f'Couldn\'t connect to {ip} on port {port}')


class HostInformation(tkinter.Tk):
    def __init__(self):
        super().__init__()
        setIcon(self)
        self.geometry('350x150')
        self.title("Chat app: Waiting for a client to join")
        self.resizable(False, False)

        self.waitMessage = ttk.Label(self, text='Join information: ')
        self.waitMessage.pack(pady=10)

        self.joinInfo = ttk.Label(self, text=f'IP: {self.localIP()}')
        self.joinInfo.pack(pady=10)

        self.joinInfo = ttk.Label(self, text=f'Port: {CHAT_PORT}')
        self.joinInfo.pack(pady=10)

        self.socket = socket.socket()
        self.socket.bind((self.localIP(), CHAT_PORT))

        self.waiter = OffThreadClientWaiter(self, self.socket)
        self.waiter.daemon = True
        self.waiter.start()

        def on_connect_func(x): return self.onConnect()
        self.bind('<<onConnect>>', on_connect_func)

        def on_error_func(x): return self.onError()
        self.bind('<<onError>>', on_error_func)

    def localIP(self):
        return socket.gethostbyname(socket.gethostname())

    def onConnect(self):
        self.destroy()
        self.waiter.join()
        win = ChatScreen('H', self.socket_connection)
        win.mainloop()

    def onError(self):
        messagebox.showerror('Error while trying to establish a connection',
                             'Couldn\'t connect to the client')
        self.socket.close()
        self.destroy()
        self.waiter.join()


class SelectChatTypeWindow(tkinter.Tk):
    def __init__(self):
        super().__init__()
        setIcon(self)
        self.geometry('350x150')
        self.title("Chat app: Select chat type")
        self.resizable(False, False)
        self.selected_app = tkinter.StringVar(self)

        self.appTypeHost = ttk.Radiobutton(
            self, text='Host chat', variable=self.selected_app, value='H')
        self.appTypeHost.grid(padx=20, pady=20, column=1,
                              row=0, sticky=tkinter.NE)
        self.appTypeJoin = ttk.Radiobutton(
            self, text='Join chat', variable=self.selected_app, value='J')
        self.appTypeJoin.grid(padx=20, pady=20, column=1,
                              row=1, sticky=tkinter.SE)

        self.appTypeLabel = ttk.Label(self, text='Select chat type: ')
        self.appTypeLabel.grid(pady=20, padx=20, column=0,
                               row=0, sticky=tkinter.NS + tkinter.W)

        self.enterButton = ttk.Button(
            self, text='Enter', command=self.enterAction)
        self.enterButton.grid(pady=20, padx=20, column=0,
                              row=1, sticky=tkinter.NS + tkinter.W)

        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def enterAction(self):
        selected = self.selected_app.get()
        if selected:
            self.destroy()

            if selected == 'H':
                win = HostInformation()
                win.mainloop()
            elif selected == 'J':
                win = ClientConnectScreen()
                win.mainloop()


if __name__ == "__main__":
    
    Path("./Downloads").mkdir(parents=True, exist_ok=True)
    SelectChatType = SelectChatTypeWindow()
    SelectChatType.mainloop()
