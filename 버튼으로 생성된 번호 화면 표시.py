import tkinter
import tkinter.font
import random

lotto_num = range(1,46)

def buttonClick():
    label = tkinter.Label(window, text=str(random.sample(lotto_num,6)))
    label.pack()
    
window=tkinter.Tk()
window.title("lotto")
window.geometry("400x200")
window.resizable(False, False)

button = tkinter.Button(window, overrelief="solid",text="번호확인", width=15, command=buttonClick, repeatdelay=1000, repeatinterval=100)
button.pack()

window.mainloop()