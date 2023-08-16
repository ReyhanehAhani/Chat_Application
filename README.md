# Chat Application Readme

This Python script implements a simple chat application with a graphical user interface (GUI) using the Tkinter library. The application allows users to either host a chat room or join an existing chat room. Users can exchange text messages and images in the chat room. The application has the following main features:

## Dependencies

The code requires the following Python libraries to be installed:
- `collections`
- `io`
- `random`
- `socket`
- `threading`
- `tkinter` (for GUI)
- `PIL` (Python Imaging Library, also known as Pillow)
- `webbrowser`

## Running the Application

To run the chat application, execute the script in a Python interpreter. The script will display a GUI window where the user can choose to host a chat room or join an existing chat room.

- **Host Chat**: Selecting this option will start a chat room where other users can join. The host can exchange messages and images with the connected users.

- **Join Chat**: Selecting this option will prompt the user to enter the IP address and port number of the host's chat room. Upon successful connection, the user can participate in the chat by exchanging messages and images.

## GUI Components

The code defines several classes for creating different GUI components:
- `ScrollableFrame`: A custom widget that provides a scrollable frame for displaying messages.
- `ChatScreen`: Represents the main chat screen where messages and images are displayed and exchanged.
- `ClientConnectScreen`: Represents the screen where a user can enter the IP address and port number to join an existing chat room.
- `HostInformation`: Represents the screen displayed when a user hosts a chat room, providing information about the host's IP address and port number.
- `SelectChatTypeWindow`: Represents the initial screen where the user selects whether to host a chat or join an existing one.

## Communication

- Messages are exchanged over sockets using TCP/IP.
- The `Message` class is used to encapsulate messages with a message type.
- The `OffThreadClientWaiter`, `OffThreadMsgReciver`, and `OffThreadImageSend` classes handle communication in separate threads to avoid blocking the GUI thread.

## User Interaction

- Users can send text messages by typing in the text entry field and clicking the "Send message" button.
- Users can upload images and send them to the chat room using the "Upload message" button.
- Clicking on an uploaded image opens the image in the default web browser for viewing.
- Users can close the application using the GUI window's close button.

## Application Flow

1. The application starts by creating a directory named "Downloads" for storing downloaded images.
2. The user is presented with the option to select whether to host or join a chat room.
3. If the user selects "Host Chat," the HostInformation screen is displayed, showing the host's IP address and port number. The host's chat room starts listening for incoming connections.
4. If the user selects "Join Chat," the ClientConnectScreen is displayed, allowing the user to enter the host's IP address and port number to connect.
5. Once connected, the ChatScreen is displayed, where users can exchange messages and images.
6. Messages and images are displayed in the ScrollableFrame on the ChatScreen.
7. Users can close the chat window to exit the application.

## Notes

- The code has comments explaining its functionality and structure.
- The code handles socket communication and GUI elements using separate threads to prevent the GUI from becoming unresponsive during communication.
