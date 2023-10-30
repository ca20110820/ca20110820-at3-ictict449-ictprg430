from abc import abstractmethod
from typing import Any, Iterable
import paho.mqtt.client as paho
import threading
import sys
import tkinter as tk

from smartpark.mqtt_device import MqttDevice


class IDisplay(MqttDevice):
    def __init__(self, config: dict, display_topic: str, *args, **kwargs):
        super().__init__(config, *args, **kwargs)
        self.display_topic = display_topic
        self.client.subscribe(self.display_topic)
        self.client.on_message = self.on_message

    @abstractmethod
    def start_listening(self):
        pass

    @abstractmethod
    def on_message(self, client: paho.Client, userdata: Any, message: paho.MQTTMessage):
        """Implement Event-handler"""
        pass


class WindowedDisplay:
    """Displays values for a given set of fields as a simple GUI window. Use .show() to display the window; use
    .update() to update the values displayed.
    """

    DISPLAY_INIT = '– – –'
    SEP = ':'  # field name separator

    def __init__(self, title: str, display_fields: Iterable[str]):
        """Creates a Windowed (tkinter) display to replace sense_hat display. To show the display (blocking) call
        .show() on the returned object.

        Parameters
        ----------
        title : str
            The title of the window (usually the name of your carpark from the config)
        display_fields : Iterable
            An iterable (usually a list) of field names for the UI. Updates to values must be presented in a dictionary
            with these values as keys.
        """
        self.window = tk.Tk()
        self.window.title(f'{title}: Parking')
        self.window.geometry('1400x400')
        self.window.resizable(False, False)
        self.display_fields = display_fields

        self.gui_elements = {}
        for i, field in enumerate(self.display_fields):

            # create the elements
            self.gui_elements[f'lbl_field_{i}'] = tk.Label(
                self.window, text=field+self.SEP, font=('Arial', 50))
            self.gui_elements[f'lbl_value_{i}'] = tk.Label(
                self.window, text=self.DISPLAY_INIT, font=('Arial', 50))

            # position the elements
            self.gui_elements[f'lbl_field_{i}'].grid(
                row=i, column=0, sticky=tk.E, padx=5, pady=5)
            self.gui_elements[f'lbl_value_{i}'].grid(
                row=i, column=2, sticky=tk.W, padx=10)

    def show(self):
        """Display the GUI. Blocking call."""
        self.window.mainloop()

    def update(self, updated_values: dict):
        """Update the values displayed in the GUI. Expects a dictionary with keys matching the field names passed to
        the constructor.
        """
        for field in self.gui_elements:
            if field.startswith('lbl_field'):
                field_value = field.replace('field', 'value')
                self.gui_elements[field_value].configure(
                    text=updated_values[self.gui_elements[field].cget('text').rstrip(self.SEP)])
        self.window.update()


class TkGUIDisplay(IDisplay):
    fields = ['Available bays', 'Temperature', 'At']  # determines what fields appear in the UI

    def __init__(self, config: dict, display_topic: str):
        super().__init__(config, display_topic)

        self.start_listening()

        self.window = WindowedDisplay('Moondalup', TkGUIDisplay.fields)
        self.window.show()

    def start_listening(self):
        """Define the Event Loop"""
        thread = threading.Thread(target=self.client.loop_forever, daemon=True)
        thread.start()

    def on_message(self, client: paho.Client, userdata: Any, message: paho.MQTTMessage):
        data = message.payload.decode()
        msg_str = data.split(';')  # List[str] := ["<spaces>", "<temperature>", "<time>"]

        field_values = dict(zip(TkGUIDisplay.fields, [
            f'{msg_str[0]}',
            f'{msg_str[1]}℃',
            f'{msg_str[2]}'
        ]))

        # When you get an update, refresh the display.
        self.window.update(field_values)


class ConsoleDisplay(IDisplay):
    def __init__(self, config: dict, display_topic: str, *args, **kwargs):
        super().__init__(config, display_topic)
        self.start_listening()

    def start_listening(self):
        self.client.loop_forever()

    def on_message(self, client: paho.Client, userdata: Any, message: paho.MQTTMessage):
        data = message.payload.decode()  # "<Entry|Exit>,<temperature>"
        msg_str = data.split(';')  # List[str] := ["<spaces>", "<temperature>", "<time>"]

        if "quit" in message.topic:  # Could use decorator
            exit()

        print("Available Parking Bays:", msg_str[0])
        print("Temperature:", msg_str[1])
        print("Time:", msg_str[2])
        print("=" * 100)
