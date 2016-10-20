import matplotlib
from matplotlib import style
import matplotlib.animation as animation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
import tkinter as tk
from tkinter import ttk
from matplotlib import pyplot as plt
import serial.tools.list_ports
import numpy as np
import threading
import time
from tkinter import filedialog
from tkinter import messagebox
from matplotlib.widgets import RectangleSelector
from datetime import datetime

matplotlib.use("TkAgg")  # backhand of matplotlib

style.use("ggplot")

LARGE_FONT = ("Cambria italic", 12)  # Custom font


class TutorialPopUp(tk.Toplevel):
    """Popup widget. Displays the tutorial info"""

    def __init__(self, parent, title=None):

        tk.Toplevel.__init__(self, parent)
        self.transient(parent)

        if title:
            self.title(title)

        self.parent = parent

        self.result = None

        body = tk.Frame(self)
        self.initial_focus = self.body(body)
        body.pack(padx=5, pady=5)

        # self.buttonbox()
        self.box = ttk.Frame(self)

        # self.initial_focus = self.combo_box
        self.s = ttk.Scrollbar(self.box)
        self.t = tk.Text(self.box, height=10, width=85)
        self.s.pack(side=tk.RIGHT, fill=tk.Y)
        self.t.pack(side=tk.RIGHT, fill=tk.Y)
        self.s.config(command=self.t.yview)
        self.t.config(yscrollcommand=self.s.set)
        self.read_tutorial_txt()
        self.t.config(state=tk.DISABLED)

        self.photo = tk.PhotoImage(file="tut_image.gif")
        self.label1 = ttk.Label(self.box, image=self.photo)
        self.label1.image = self.photo  # keep a reference!
        self.label1.pack()

        self.bind("<Escape>", self.cancel)
        self.w2 = ttk.Button(self.box, text="Exit", width=10, command=self.cancel)
        self.w2.pack(side=tk.LEFT, padx=5, pady=5)
        self.box.pack()

        self.grab_set()

        if not self.initial_focus:
            self.initial_focus = self

        self.protocol("WM_DELETE_WINDOW", self.cancel)

        self.geometry("+%d+%d" % (parent.winfo_rootx() + 50,
                                  parent.winfo_rooty() + 50))

        self.initial_focus.focus_set()

        self.wait_window(self)

    #
    # construction hooks

    def read_tutorial_txt(self):
        with open("tutorial.txt", "r") as tutorial:
            lines = tutorial.read()
            self.t.insert(tk.END, lines)

    def body(self, master):
        # create dialog body.  return widget that should have
        # initial focus.  this method should be overridden
        pass

    def cancel(self, event=None):

        # put focus back to the parent window
        self.parent.focus_set()
        self.destroy()

    #
    # command hooks

    def validate(self):

        return 1  # override

    def apply(self):

        pass  # override


class DeleteKValuesPopUp(tk.Toplevel):
    """Popup widget. Displays a dropdown list for deleting Calibration values"""

    def __init__(self, parent, title=None):

        tk.Toplevel.__init__(self, parent)
        self.transient(parent)

        if title:
            self.title(title)

        self.parent = parent

        self.result = None

        body = tk.Frame(self)
        self.initial_focus = self.body(body)
        body.pack(padx=5, pady=5)

        # self.buttonbox()
        self.box = ttk.Frame(self)

        self.v = tk.StringVar()
        self.box_value = tk.StringVar()
        self.box_value.set("N/A")
        self.combo_box_list = []

        self.combo_box = ttk.Combobox(self.box, textvariable=self.box_value, font=LARGE_FONT)
        self.get_k_values()
        self.combo_box.configure(width=12, height=10)
        self.combo_box.bind("<<ComboboxSelected>>", self.listboxfunc)
        self.combo_box.pack()

        self.initial_focus = self.combo_box
        self.w1 = ttk.Button(self.box, text="Delete", width=10, command=self.ok, default=tk.ACTIVE)
        self.w1.pack(side=tk.LEFT, padx=5, pady=5)
        self.w2 = ttk.Button(self.box, text="Cancel", width=10, command=self.cancel)
        self.w2.pack(side=tk.LEFT, padx=5, pady=5)

        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)

        self.box.pack()

        self.grab_set()

        if not self.initial_focus:
            self.initial_focus = self

        self.protocol("WM_DELETE_WINDOW", self.cancel)

        self.geometry("+%d+%d" % (parent.winfo_rootx() + 50,
                                  parent.winfo_rooty() + 50))

        self.initial_focus.focus_set()

        self.wait_window(self)

    #
    # construction hooks

    def body(self, master):
        # create dialog body.  return widget that should have
        # initial focus.  this method should be overridden
        pass

    def ok(self, event=None):
        if not self.validate():
            self.initial_focus.focus_set()  # put focus back
            return

        f = open("kvalues.txt", "r")
        lines = f.readlines()
        f.close()
        f = open("kvalues.txt", "w")
        for line in lines:
            if line != self.v.get():
                f.write(line)

        f.close()

        self.withdraw()
        self.update_idletasks()

        self.apply()

        self.cancel()

    def cancel(self, event=None):

        # put focus back to the parent window
        self.parent.focus_set()
        self.destroy()

    #
    # command hooks

    def validate(self):

        return 1  # override

    def apply(self):

        pass  # override

    def get_k_values(self):
        self.combo_box_list.clear()
        # self.listbox.delete(0, tk.END)
        with open("kvalues.txt", "r") as kvalues:
            lines = kvalues.readline()
            while lines:
                self.combo_box_list.append(lines)
                # self.listbox.insert(tk.END, lines)
                lines = kvalues.readline()

        self.combo_box['values'] = self.combo_box_list

    def listboxfunc(self, event):
        # kkvalue = self.listbox.get(tk.ACTIVE)

        kkvalue = self.combo_box.get()
        self.v.set(kkvalue)


class MyPlots(plt.Figure):
    """Main plot class. Takes the data from the datasource and plots it live"""

    def __init__(self, datasource):
        plt.Figure.__init__(self)
        self.DataAcquisition = datasource

        self.cList = np.array([], dtype=float)
        self.vList = np.array([], dtype=float)
        self.axes1 = self.add_subplot(211)
        self.suptitle("Measurement", fontsize=20)
        self.list1 = np.array([], dtype=float)
        self.list2 = np.array([], dtype=float)

        self.axes1.set_gid("A")
        self.axes2 = self.add_subplot(212)
        self.axes2.set_gid("B")

        self.m = 0.0
        self.c = 0.0

        self.start_stop = True

    def animate(self, i):

        '''Plots a live graph.'''

        if self.start_stop:
            self.axes1.clear()
            # self.axes1.set_ylim([-500, 2500])
            self.axes1.set_ymargin(0.2)
            self.axes1.set_ylabel("Voltage [mV]")
            self.axes1.set_xlabel("Time [s]")

            try:
                self.axes1.plot(self.DataAcquisition.timeList, self.DataAcquisition.voltageList, "#00A3E0")
            except ValueError:
                print("timelist len : ", len(self.DataAcquisition.timeList))
                print("vlist len : ", len(self.DataAcquisition.voltageList))
                pass
            self.axes1.plot(self.list2, self.list1, "ro")

        self.axes2.clear()
        self.axes2.set_ymargin(0.3)
        # self.axes2.set_ylim([-100, 2500])
        # self.axes2.set_xlim([0, 20])
        self.axes2.set_xmargin(0.3)
        self.axes2.set_ylabel("Voltage [mV]")
        self.axes2.set_xlabel("Concentration [mg/ml]")
        self.axes2.plot(self.cList, self.vList, "ro")

        if self.m:
            self.axes2.plot(self.cList, self.m * self.cList + self.c, 'b')

    def linefit(self):
        a = np.vstack([self.cList, np.ones(len(self.cList))]).T
        self.m, self.c = np.linalg.lstsq(a, self.vList)[0]

    def find_nearest(self, value):
        '''Finds the index of the nearest values in an array, to be removed from the graph.'''

        idx = (np.abs(self.cList - value)).argmin()
        self.cList = np.delete(self.cList, idx)
        self.vList = np.delete(self.vList, idx)

    def find_nearest_sorted(self, value):
        '''Finds the index of the element that is closest to the given value, in a sorted numpy array, '''

        idx = np.searchsorted(self.DataAcquisition.timeList, value, side="left")
        return idx

    def get_volt_and_concent(self, concent, time1, time2):

        '''
        Takes the tipped in concentration value as concent, and takes the avarage of the selected voltage
        values. Saves the concent and avarage voltage to corresponding arrays, to be ploted.
        '''

        self.cList = np.append(self.cList, concent)
        idx1 = self.find_nearest_sorted(time1)
        idx2 = self.find_nearest_sorted(time2)

        average = np.mean(self.DataAcquisition.voltageList[idx1:idx2])

        self.vList = np.append(self.vList, [float(average)])

        self.list1 = np.append(self.list1, self.DataAcquisition.voltageList[idx1:idx2])
        self.list2 = np.append(self.list2, self.DataAcquisition.timeList[idx1:idx2])
        self.axes1.plot(self.list2, self.list1, "ro")
        # self.axes1.plot(self.list2, self.list1, "blue", linewidth=2)

    def clear_plots(self):
        '''Clears the data lists from data source. Deletes all values from own arrays. Clears the sub_plots'''

        self.DataAcquisition.clear_data_lists()
        self.m = 0.0
        self.vList = np.array([], dtype=float)
        self.cList = np.array([], dtype=float)
        self.list1 = np.array([], dtype=float)
        self.list2 = np.array([], dtype=float)
        self.axes1.clear()
        self.axes2.clear()

    def get_slope(self):
        return self.m

    def plot_static_data(self):
        '''Plots the not-live data, loaded from the datasource'''

        self.start_stop = False
        self.DataAcquisition.load_data()
        print(len(self.DataAcquisition.voltageList), "len voltage")
        print(len(self.DataAcquisition.timeList), "len time")

        self.axes1.clear()
        self.axes1.set_ymargin(0.2)
        self.axes1.set_ylabel("Voltage [mV]")
        self.axes1.set_xlabel("Time [s]")

        self.axes1.plot(self.DataAcquisition.timeList, self.DataAcquisition.voltageList, "#00A3E0")

    def flip_start_stop(self):
        self.start_stop = not self.start_stop


class RemoveDataPointPopup(tk.Toplevel):
    '''Popup widget. Asks for confirmation to remove the clicked data point on the second plot'''

    def __init__(self, parent, title=None):

        tk.Toplevel.__init__(self, parent)
        self.transient(parent)

        if title:
            self.title(title)

        self.parent = parent

        self.result = None

        body = tk.Frame(self)
        self.initial_focus = self.body(body)
        body.pack(padx=5, pady=5)

        # self.buttonbox()
        self.box = ttk.Frame(self)
        self.w1 = ttk.Button(self.box, text="OK", width=10, command=self.ok, default=tk.ACTIVE)
        self.w1.pack(side=tk.LEFT, padx=5, pady=5)
        self.w2 = ttk.Button(self.box, text="Cancel", width=10, command=self.cancel)
        self.w2.pack(side=tk.LEFT, padx=5, pady=5)

        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)
        self.box.pack()

        self.grab_set()

        if not self.initial_focus:
            self.initial_focus = self

        self.protocol("WM_DELETE_WINDOW", self.cancel)

        self.geometry("+%d+%d" % (parent.winfo_rootx() + 450,
                                  parent.winfo_rooty() + 450))

        self.initial_focus.focus_set()

        self.wait_window(self)

    def body(self, master):

        pass

    def ok(self, event=None):
        if not self.validate():
            self.initial_focus.focus_set()  # put focus back
            return
        self.parent.find_and_remove_nearest()
        self.withdraw()
        self.update_idletasks()

        self.apply()

        self.cancel()

    def cancel(self, event=None):

        # put focus back to the parent window
        self.parent.focus_set()
        self.destroy()

    #
    # command hooks

    def validate(self):

        return 1  # override

    def apply(self):

        pass  # override


class EnterConcentrationPopup(tk.Toplevel):
    '''Popup widget. Takes the entered concentration value to processed '''

    def __init__(self, parent, title=None):

        tk.Toplevel.__init__(self, parent)
        self.transient(parent)

        if title:
            self.title(title)

        self.parent = parent

        self.result = None

        # body = tk.Frame(self)
        # self.initial_focus = self.body(body)
        # body.pack(padx=15, pady=5)

        # self.buttonbox()
        self.box = ttk.Frame(self)
        self.e = ttk.Entry(self.box)

        self.e.pack(padx=6)
        self.initial_focus = self.e
        self.w1 = ttk.Button(self.box, text="OK", width=10, command=self.ok, default=tk.ACTIVE)
        self.w1.pack(side=tk.LEFT, padx=6, pady=5)
        self.w2 = ttk.Button(self.box, text="Cancel", width=10, command=self.cancel)
        self.w2.pack(side=tk.LEFT, padx=6, pady=5)

        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)

        self.box.pack()

        self.grab_set()

        if not self.initial_focus:
            self.initial_focus = self

        self.protocol("WM_DELETE_WINDOW", self.cancel)

        self.geometry("+%d+%d" % (parent.winfo_rootx() + 200,
                                  parent.winfo_rooty() + 200))

        self.initial_focus.focus_set()

        self.wait_window(self)

    #
    # construction hooks

    def body(self, master):
        # create dialog body.  return widget that should have
        # initial focus.  this method should be overridden

        pass

    # def buttonbox(self):
    #     # add standard button box. override if you don't want the
    #     # standard buttons
    #
    #     box = ttk.Frame(self)
    #     e = ttk.Entry(box)
    #
    #     e.pack(padx=5)
    #
    #     w1 = ttk.Button(box, text="OK", width=10, command=self.ok, default=tk.ACTIVE)
    #     w1.pack(side=tk.LEFT, padx=5, pady=5)
    #     w2 = ttk.Button(box, text="Cancel", width=10, command=self.cancel)
    #     w2.pack(side=tk.LEFT, padx=5, pady=5)
    #
    #     self.bind("<Return>", self.ok)
    #     self.bind("<Escape>", self.cancel)
    #
    #     box.pack()
    #
    # #
    # standard button semantics

    def ok(self, event=None):
        if not self.validate():
            self.initial_focus.focus_set()  # put focus back
            return

        concent = float(self.e.get())
        self.parent.get_volt_and_concent(concent)

        self.withdraw()
        self.update_idletasks()

        self.apply()

        self.cancel()

    def cancel(self, event=None):

        # put focus back to the parent window
        self.parent.focus_set()
        self.destroy()

    #
    # command hooks

    def validate(self):

        return 1  # override

    def apply(self):

        pass  # override


class DataAcquisition:
    '''Data source. Finds the corresponding serial port and starts taking data. '''

    def __init__(self):
        self.start_flag = True
        self.comPort = self.find_port()
        self.arduino = serial.Serial(self.comPort, 9600, timeout=.1)
        self.voltageList = np.array([], dtype=float)
        self.timeList = np.array([], dtype=float)
        self.time = 0.0
        self.now = time.time()
        self.before = time.time()
        self.start_read_port()

    def find_port(self):
        ports = list(serial.tools.list_ports.comports())
        for eachPort in ports:
            print(eachPort)
            if "Arduino" in eachPort[1]:
                print(eachPort[0])
                portname = eachPort[0]
                return portname

    def read_port(self):

        '''
        Takes voltage values from the serial port in milivolt.
        Calculates the time passed in the meanwhile.
        Saves the data to corresponding numpy arrays
        '''
        while True:
            data = self.arduino.readline()
            if data and self.start_flag:
                try:

                    voltage = float((data.decode())[0:-2])
                    # print(voltage)
                    self.voltageList = np.append(self.voltageList, [voltage])
                    self.now = time.time()
                    difference = self.now - self.before
                    self.time = difference + self.time
                    self.timeList = np.append(self.timeList, [self.time])
                    self.before = time.time()
                except ValueError:
                    print("conversion failed")

            time.sleep(0.3)
        else:
            print("serial stopped")

    def start_read_port(self):
        t1 = threading.Thread(target=self.read_port)
        t1.setDaemon(True)
        t1.start()

    def clear_data_lists(self):

        '''Empties the numpy arrays '''

        self.time = 0.0
        self.timeList = np.array([], dtype=float)
        self.voltageList = np.array([], dtype=float)

    def save_data(self):

        '''Saves the values in the numpy arrays to a txt file via a filedilaog'''

        f = filedialog.asksaveasfile(mode='w', defaultextension=".txt")
        if f is None:  # asksaveasfile return `None` if dialog closed with "cancel".
            return
        for (volt, time1) in zip(self.voltageList, self.timeList):
            f.write("{}".format(volt))
            f.write(" {:.3f} \n".format(time1))

        f.close()

    def load_data(self):

        '''Loads offline data from a txt file. Pauses reading from serial port'''

        self.stop_data_acquisition()
        self.clear_data_lists()

        fname = filedialog.askopenfilename(filetypes=(("Text Files", ".txt"),

                                                      ("All Files", "*.*")))
        if fname:
            print(fname)

            with open(fname, "r") as myfile:
                lines = myfile.readline()
                while lines:
                    lines = myfile.readline()
                    if lines:
                        self.voltageList = np.append(self.voltageList, [float(lines.split(" ")[0])])
                        self.timeList = np.append(self.timeList, [float(lines.split(" ")[1])])

    def stop_data_acquisition(self):
        self.start_flag = False

    def start_data_acquisition(self):
        self.start_flag = True
        self.before = time.time()


class CalibrationFrame(tk.Frame):
    '''Main GUI frame for the calibration page. Takes another frame (CalibrationPage) as master'''

    def __init__(self, master):
        tk.Frame.__init__(self, master)
        self.master = master
        # self.config(relief="sunken", borderwidth=1)
        self.grid_rowconfigure(1, weight=1)
        # self.grid_columnconfigure(0, weight=1)
        self.v_dndc = tk.StringVar()
        self.v_dndc.set("N/A")
        self.v1 = tk.StringVar()
        self.v1.set("N/A")
        self.v2_k = tk.StringVar()

        self.v2_k.set("?")
        self.klist = []

        self.formula_frame = tk.Frame(self)
        self.formula_frame.grid(row=0, column=0, columnspan=2)
        self.label1 = ttk.Label(self.formula_frame, text="mV          = \u212A       c", font=LARGE_FONT)
        self.label1.grid(row=0, column=0, columnspan=2, pady=(20, 20), padx=(25, 0))

        self.label_dc = ttk.Label(self.formula_frame, text="dc", font=LARGE_FONT)
        self.label_dc.grid(column=0, row=0, columnspan=2, pady=(24, 0), padx=(115, 0), sticky="w")

        self.label_ = ttk.Label(self.formula_frame, text="___", font=LARGE_FONT)
        self.label_.grid(column=0, row=0, columnspan=2, pady=(0, 12), padx=(115, 0), sticky="w")

        self.label_dn = ttk.Label(self.formula_frame, text="dn", font=LARGE_FONT)
        self.label_dn.grid(column=0, row=0, columnspan=2, pady=(0, 24), padx=(115, 0), sticky="w")

        self.label123 = ttk.Label(self.formula_frame, text="output", font=("Cambria italic", 8))
        self.label123.grid(row=0, columnspan=2, pady=(30, 20), padx=(49, 0), sticky="w")

        self.label4 = ttk.Label(self, text=" =", font=LARGE_FONT)
        self.label4.grid(column=0, row=1, sticky="w", pady=(0, 0), padx=(20, 0))

        self.label_dc = ttk.Label(self, text="dc", font=LARGE_FONT)
        self.label_dc.grid(column=0, row=1, pady=(22, 0), sticky="w")

        self.label_ = ttk.Label(self, text="___", font=LARGE_FONT)
        self.label_.grid(column=0, row=1, pady=(0, 10), sticky="w")

        self.label_dn = ttk.Label(self, text="dn", font=LARGE_FONT)
        self.label_dn.grid(column=0, row=1, pady=(0, 20), sticky="w")

        self.label412 = ttk.Label(self, text="[ml/g]", font=LARGE_FONT)
        self.label412.grid(column=2, row=1, sticky="w", pady=(0, 0))

        self.box_value = tk.StringVar()
        self.box_value.set("N/A")
        self.combo_box_list = []

        self.combo_box = ttk.Combobox(self, textvariable=self.box_value, font=LARGE_FONT)
        self.get_dndc_values()
        self.combo_box.configure(width=12, height=10)
        self.combo_box.bind("<<ComboboxSelected>>", self.combobox_func)
        self.combo_box.grid(column=1, row=1, pady=(20, 20))

        # self.label2 = ttk.Label(self, text="c = ", font=LARGE_FONT)
        # self.label2.grid(column=0, row=2, sticky="w", pady=(0, 20))
        # self.label23 = ttk.Label(self, text="299792458 m/s", font=LARGE_FONT)
        # self.label23.grid(column=1, row=2, sticky="w", pady=(0, 20))

        self.label5 = ttk.Label(self, text="Slope = ", font=LARGE_FONT)
        self.label5.grid(column=0, row=3, sticky="sw", pady=(20, 20))
        self.label3 = ttk.Label(self, textvariable=self.v1, font=LARGE_FONT)
        self.label3.grid(column=1, row=3, sticky="sw", pady=(20, 20))

        self.label41 = ttk.Label(self, text="\u212A = ", font=LARGE_FONT)
        self.label41.grid(column=0, row=4, sticky="w", pady=(0, 20))
        self.label411 = ttk.Label(self, textvariable=self.v2_k, font=LARGE_FONT)
        self.label411.grid(column=1, row=4, sticky="w", pady=(0, 20))

        # self.btn2 = ttk.Button(self, text="Fit the Line!", command=self.linefit)
        # self.btn2.grid(column=0, row=5, sticky="ew", columnspan=3)

        self.btn = ttk.Button(self, text="Solve the equation!", command=self.solve_equation)
        self.btn.grid(column=0, row=6, sticky="ew", columnspan=3)
        # self.btn.configure(state="disabled")

        self.btn4 = ttk.Button(self, text="Save calibration", command=self.save_k_value)
        self.btn4.grid(column=0, row=7, columnspan=3, sticky="ew")
        self.btn4.configure(state="disabled")

    def save_k_value(self):
        '''Saves the calculated calibration value to a txt file. '''

        with open("kvalues.txt", 'a') as kvalues:
            string = self.v2_k.get() + " " + datetime.now().strftime("%d-%m-%y %H:%M") + "\n"
            kvalues.write(string)

    def print_slope(self):
        slope = self.master.get_slope()
        ak = "{:8.4f}".format(slope)
        self.v1.set(ak)

    def linefit(self):

        self.master.plot_linefit()
        self.print_slope()

    def solve_equation(self):

        '''Solves the equation to calculate the calibration values. Enables the save button'''

        self.linefit()
        self.btn4.configure(state="enabled")
        ak = self.combo_box.get().split(' ')[0]
        print("ak, ", ak)
        self.v_dndc.set(ak)
        floatt = self.v_dndc.get()  # this is the dndc value tipped in by the user
        print(floatt)
        try:
            slope = self.master.get_slope()
            answer = slope / float(floatt)
            self.v2_k.set("{:.4f}".format(answer))
        except ValueError:
            print("Value error during solve_equation!")

    def quit(self):
        self.destroy()

    def combobox_func(self, event):
        kkvalue = self.combo_box.get()
        self.v_dndc.set(kkvalue)

    def get_dndc_values(self):
        '''Reads the saved dn_dc values from a text file and displays them in commbox.'''
        self.combo_box_list.clear()
        # self.listbox.delete(0, tk.END)
        with open("dndc_list.txt", "r") as kvalues:
            lines = kvalues.readline()
            while lines:
                self.combo_box_list.append(lines)
                # self.listbox.insert(tk.END, lines)
                lines = kvalues.readline()

        self.combo_box['values'] = self.combo_box_list


class MeasurementFrame(tk.Frame):
    '''Main GUI frame for the measurement page. Takes another frame (MeasurePage) as master. '''

    def __init__(self, master):
        tk.Frame.__init__(self, master)
        self.master = master
        # self.config(relief="sunken", borderwidth=1)
        self.grid_rowconfigure(1, weight=1)
        # self.grid_columnconfigure(0, weight=1)
        self.v = tk.StringVar()
        self.v1 = tk.StringVar()
        self.v1.set("N/A")
        self.v2 = tk.StringVar()
        self.v.set("N/A")
        self.v2.set("?             [ml/g]")

        # self.label1 = ttk.Label(self, text="Mv=K dn/dc c", font=("Cambria math", 12))
        # self.label1.grid(row=0, column=0, columnspan=2)

        self.formula_frame = tk.Frame(self)
        self.formula_frame.grid(row=0, column=0, columnspan=2)
        self.label1 = ttk.Label(self.formula_frame, text="mV          = \u212A       c", font=LARGE_FONT)
        self.label1.grid(row=0, column=0, columnspan=2, pady=(20, 20), padx=(25, 0))

        self.label_dc = ttk.Label(self.formula_frame, text="dc", font=LARGE_FONT)
        self.label_dc.grid(column=0, row=0, columnspan=2, pady=(24, 0), padx=(115, 0), sticky="w")

        self.label_ = ttk.Label(self.formula_frame, text="___", font=LARGE_FONT)
        self.label_.grid(column=0, row=0, columnspan=2, pady=(0, 12), padx=(115, 0), sticky="w")

        self.label_dn = ttk.Label(self.formula_frame, text="dn", font=LARGE_FONT)
        self.label_dn.grid(column=0, row=0, columnspan=2, pady=(0, 24), padx=(115, 0), sticky="w")

        self.label123 = ttk.Label(self.formula_frame, text="output", font=("Cambria italic", 8))
        self.label123.grid(row=0, columnspan=2, pady=(30, 20), padx=(49, 0), sticky="w")

        # self.label1 = ttk.Label(self, text="mV          = \u212A        c", font=LARGE_FONT)
        # self.label1.grid(row=0, column=0, columnspan=2, pady=(20, 20))
        # self.label123 = ttk.Label(self, text="output", font=("Cambria italic", 8))
        # self.label123.grid(row=0, columnspan=2, pady=(15, 0), padx=(47, 0), sticky="w")
        #
        # self.label_dc = ttk.Label(self, text="dc", font=LARGE_FONT)
        # self.label_dc.grid(column=0, row=0, columnspan=2, pady=(30, 0), padx=(113, 0), sticky="w")
        #
        # self.label_ = ttk.Label(self, text="___", font=LARGE_FONT)
        # self.label_.grid(column=0, row=0, columnspan=2, pady=(0, 8), padx=(114, 0), sticky="w")
        #
        # self.label_dn = ttk.Label(self, text="dn", font=LARGE_FONT)
        # self.label_dn.grid(column=0, row=0, columnspan=2, pady=(0, 18), padx=(113, 0), sticky="w")

        self.label4 = ttk.Label(self, text="K =", font=LARGE_FONT)
        self.label4.grid(column=0, row=1, sticky="nw", pady=(20, 20))
        self.box_value = tk.StringVar()
        self.box_value.set("N/A")
        self.combo_box_list = []

        self.combo_box = ttk.Combobox(self, textvariable=self.box_value, font=LARGE_FONT)
        self.get_k_values()
        self.combo_box.configure(width=15, height=10)
        self.combo_box.bind("<<ComboboxSelected>>", self.listboxfunc)
        self.combo_box.grid(column=1, row=1, pady=(20, 20))

        self.label5 = ttk.Label(self, text="Slope = ", font=LARGE_FONT)
        self.label5.grid(column=0, row=3, sticky="sw", pady=(10, 20))
        self.label3 = ttk.Label(self, textvariable=self.v1, font=LARGE_FONT)
        self.label3.grid(column=1, row=3, sticky="w", pady=(10, 20))

        self.label41 = ttk.Label(self, textvariable=self.v2, font=LARGE_FONT)
        self.label41.grid(column=1, row=4, sticky="w", pady=(0, 0))

        self.label4 = ttk.Label(self, text=" =", font=LARGE_FONT)
        self.label4.grid(column=0, row=4, sticky="w", pady=(0, 0), padx=(20, 0))

        self.label_dc1 = ttk.Label(self, text="dc", font=LARGE_FONT)
        self.label_dc1.grid(column=0, row=4, pady=(23, 0), sticky="w")

        self.label_1 = ttk.Label(self, text="___", font=LARGE_FONT)
        self.label_1.grid(column=0, row=4, pady=(0, 10), sticky="w")

        self.label_dn1 = ttk.Label(self, text="dn", font=LARGE_FONT)
        self.label_dn1.grid(column=0, row=4, pady=(0, 20), sticky="w")

        self.btn1 = ttk.Button(self, text="Solve the equation!", command=self.solve_equation)
        self.btn1.grid(column=0, row=5, sticky="ew", columnspan=2, pady=(20, 0))

    def get_k_values(self):
        self.combo_box_list.clear()
        # self.listbox.delete(0, tk.END)
        with open("kvalues.txt", "r") as kvalues:
            lines = kvalues.readline()
            while lines:
                self.combo_box_list.append(lines)
                # self.listbox.insert(tk.END, lines)
                lines = kvalues.readline()

        self.combo_box['values'] = self.combo_box_list

    def print_slope(self):
        slope = self.master.get_slope()
        ak = "{:9.4f}".format(slope)  # formatting the float to string in a nice fashion

        self.v1.set(ak)

    def listboxfunc(self, event):
        kkvalue = self.combo_box.get()
        self.v.set(kkvalue)

    def linefit(self):
        self.master.plot_linefit()
        self.print_slope()

        print("Line Fit!")

    def solve_equation(self):
        self.linefit()
        floatt = self.v.get().split(' ')[0]  # kvalue
        print(floatt)  # dont forget to select the K ****+

        try:
            slope = self.master.get_slope()
            answer = slope / float(floatt)
            self.v2.set("{:.4f}".format(answer) + " [mg/ml]")
        except ValueError:
            print("value error during solve_equatiom")


class Container(tk.Frame):
    '''
        Master frame for Calibration and Measurement frames. Hosts filemenu buttons.
        Also serves as a middle-way communicator between GUI and Controller
    '''

    def __init__(self, master):
        tk.Frame.__init__(self, master)
        self.master = master
        self.config(relief="sunken", borderwidth=1)
        self.menubar = tk.Menu(self)

        self.filemenu = tk.Menu(self.menubar, tearoff=0)
        self.filemenu.add_command(label="Calibrate", command=lambda: master.show_frame(CalibrationPage))
        self.filemenu.add_command(label="Measure", command=lambda: master.show_frame(MeasurePage))
        self.filemenu.add_command(label="Delete K", command=self.k_val_delete)
        self.filemenu.add_separator()
        self.filemenu.add_command(label="Save Data", command=self.save_data)
        self.filemenu.add_command(label="Load Data", command=self.load_data)
        self.filemenu.add_command(label="Start Data", command=self.start_data_acquisiton)
        self.filemenu.add_separator()
        self.filemenu.add_command(label="Exit", command=self.quit)
        self.menubar.add_cascade(label="File", menu=self.filemenu)

        self.helpmenu = tk.Menu(self.menubar, tearoff=0)
        self.helpmenu.add_command(label="Tutorial", command=self.help_pop_up)
        self.menubar.add_cascade(label="Help", menu=self.helpmenu)
        tk.Tk.config(self.master, menu=self.menubar)

    def save_data(self):
        self.master.save_data()

    def k_val_delete(self):
        self.master.k_val_delete()

    def help_pop_up(self):
        self.master.help_pop_up()

    def load_data(self):
        self.master.load_data()

    def start_data_acquisiton(self):
        self.master.start_data_acquisition()


class PlotFrame(tk.Frame):
    '''Frame for hosting the canvas, toolbar and plot related buttons. Takes Controller as master.'''

    def __init__(self, master):
        tk.Frame.__init__(self, master)
        self.master = master
        self.start_stop_var = tk.StringVar()
        self.start_stop_var.set("Stop")
        # self.btn3 = ttk.Button(self, textvariable=self.start_stop_var, command=self.start_stop)
        # self.btn3.pack(side=tk.RIGHT)
        #
        # self.btn4 = ttk.Button(self, text="Clear", command=self.clear_graph)
        # self.btn4.pack(side=tk.RIGHT)

    def start_stop(self):
        self.master.start_stop()

    def clear_graph(self):
        self.master.clear_graph()

    def call_entry_popup(self):
        entry_popup = EnterConcentrationPopup(self.master, title="Concent. [mg/mL]")

    def call_help_popup(self):
        dialogg = RemoveDataPointPopup(self.master, title="Remove Check")

    def create_buttons(self):
        '''
        Creates plot related buttons. This function will be called in the canvas class,
        due to Pack geometry manager issues.
        '''
        btn3 = ttk.Button(self, textvariable=self.start_stop_var, command=self.start_stop)
        btn3.pack(side=tk.RIGHT)

        btn4 = ttk.Button(self, text="Clear", command=self.clear_graph)
        btn4.pack(side=tk.RIGHT)


class Controller(tk.Tk):  # Tk class from tk module is inherited
    '''
    Controller class. Communicates the Wiew with Model.
    Serves as a root for Gui, a master all frames are created
    '''

    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)
        self.columnconfigure(0, weight=20)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=5)

        tk.Tk.wm_title(self, "Measurement Unit")

        self.datasource = DataAcquisition()
        self.plots = MyPlots(self.datasource)
        self.container = Container(self)  # frame is also a class from Tkinter, you basicly create a frame to fill in
        self.container.grid(row=1, column=1, pady=(0, 200))

        self.plot_frame = PlotFrame(self)
        self.plot_frame.grid(row=1, column=0, sticky="news")

        self.canvass = CanvasClass(self.plots, self.plot_frame)

        self.frames = {}  # this is an emtpy dictionary that will hold different frames

        self.calibration_page = CalibrationPage(self, self.container)
        self.frames[CalibrationPage] = self.calibration_page
        self.calibration_page.grid(row=0, column=0, sticky="nsew")

        self.measurement_page = MeasurePage(self, self.container)
        self.frames[MeasurePage] = self.measurement_page
        self.measurement_page.grid(row=0, column=0, sticky="nsew")

        self.protocol("WM_DELETE_WINDOW", self.quit)

        self.show_frame(MeasurePage)
        self.ani = animation.FuncAnimation(self.plots, self.plots.animate, interval=400, blit=False)

    def save_data(self):
        self.datasource.save_data()

    def k_val_delete(self):
        popup = DeleteKValuesPopUp(self, title="Delete K values")
        self.measurement_page.MeasurementFrame.get_k_values()

    def help_pop_up(self):
        popup_tutorial = TutorialPopUp(self, title="Tutorial")

    def show_frame(self, cont):
        frame = self.frames[cont]  # takes the given argument as a dict key
        self.clear_graph()
        self.frames[MeasurePage].MeasurementFrame.get_k_values()
        if frame == self.measurement_page:
            self.plots.suptitle("Measurement", fontsize=20)
        else:
            self.plots.suptitle("Calibration", fontsize=20)

        frame.tkraise()  # raises the given frame

    def start_stop(self):

        if self.plots.start_stop:
            self.plot_frame.start_stop_var.set("Start")

        else:
            self.plot_frame.start_stop_var.set("Stop")
        self.flip_start_stop()

    def clear_graph(self):
        self.plots.clear_plots()

    def get_slope(self):
        slope = self.plots.get_slope()
        return slope

    def plot_linefit(self):
        self.plots.linefit()

    def find_and_remove_nearest(self):
        xdata = self.canvass.xdata
        self.plots.find_nearest(xdata)

    def get_volt_and_concent(self, concent):
        time1 = self.canvass.xx1
        time2 = self.canvass.xx2
        self.plots.get_volt_and_concent(concent, time1=time1, time2=time2)

    def load_data(self):

        self.plots.plot_static_data()
        self.plot_frame.start_stop_var.set("Start")
        # self.plots.flip_start_stop()

    def flip_start_stop(self):
        self.plots.flip_start_stop()

    def start_data_acquisition(self):
        self.datasource.start_data_acquisition()


class MeasurePage(tk.Frame):
    '''
    Main Frame for Measurement. Hosts the Measurement Frame.
    Takes Container as master.
     '''

    def __init__(self, controller, container):
        tk.Frame.__init__(self, container)  # the base is class is being initialised
        # self.label = ttk.Label(self, text="Measurement Unit", font=LARGE_FONT)
        # self.label.grid(row=0, column=0)
        self.controller = controller

        self.start_stop = True

        self.MeasurementFrame = MeasurementFrame(self)
        self.MeasurementFrame.grid(column=0, row=1, sticky="nw", pady=(0, 30), padx=(40, 40))

    def get_slope(self):
        slope = self.controller.get_slope()
        return slope

    def plot_linefit(self):
        self.controller.plot_linefit()


class CalibrationPage(tk.Frame):
    '''
    Main Frame for Calibration. Hosts the Calibration Frame.
    Takes another frane(Container) as master.
    '''

    def __init__(self, parent, container):
        tk.Frame.__init__(self, container)  # the base is class is being initialised
        # self.label = ttk.Label(self, text="Calibration", font=LARGE_FONT)
        # self.label.grid(row=0, column=0)  # since its such a basic example lets use pack
        self.parent = parent
        # self.plots = plots
        self.start_stop = True

        # self.button1 = ttk.Button(self, text="Back to Measure",
        #                           command=lambda: parent.show_frame(MeasurePage))
        # self.button1.grid(row=0, column=1, sticky="w")

        self.CalibrationFrame = CalibrationFrame(self)
        self.CalibrationFrame.grid(column=0, row=1, sticky="nw", pady=(0, 30), padx=(40, 40))

        # self.canvas.get_tk_widget().grid(row=1, column=0)

    def get_slope(self):
        slope = self.parent.get_slope()
        return slope

    def plot_linefit(self):
        self.parent.plot_linefit()


class CanvasClass(FigureCanvasTkAgg):
    '''Canvas for the plots. Needs a plot and master. Hosts callback functions'''

    def __init__(self, plot, master):
        FigureCanvasTkAgg.__init__(self, plot, master)
        self.plot = plot
        self.master = master
        self.get_tk_widget().pack(fill=tk.BOTH, expand=10, side=tk.TOP)
        self.callbacks.connect('button_press_event', self.callback)
        self.xdata = 0.0
        self.xx1 = 0.0
        self.xx2 = 0.0
        self.toolbar = NavigationToolbar2TkAgg(self, self.master)
        self.toolbar.pack(side=tk.LEFT, padx=5)
        self.toolbar.update()
        self.show()
        self.master.create_buttons()

        self.rs = RectangleSelector(self.plot.axes1, self.line_select_callback,
                                    drawtype='box', useblit=True, rectprops=dict(facecolor='red', edgecolor='black',
                                                                                 alpha=0.2, fill=True),
                                    button=[1, 3],  # don't use middle button
                                    minspanx=1, minspany=1,
                                    spancoords='data',
                                    interactive=False)

    def line_select_callback(self, eclick, erelease):
        self.xx1 = eclick.xdata
        self.xx2 = erelease.xdata

        self.master.call_entry_popup()

    def callback(self, event):

        if event.inaxes is not None:

            if self.toolbar.mode == "" and event.inaxes.get_gid() == 'B':
                self.xdata = event.xdata
                print("x data 2 = ", self.xdata)
                self.master.call_help_popup()


app = Controller()  # create an object of the class
app.geometry("1280x720")

app.mainloop()  # runs the mainloop
