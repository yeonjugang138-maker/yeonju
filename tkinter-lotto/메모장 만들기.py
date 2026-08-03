
from tkinter import *
from tkinter.filedialog import *

# 텍스트창을 아무것도 안 쓰인 상태로!
def new_file():
    text_area.delete(1.0,END)

# 현재 쓰여진 내용을 파일로 저장하기
def save_file():
    f = asksaveasfile(mode = "w", defaultextension=".txt",filetypes=[('Text files', '.txt')])
    text_save = str(text_area.get(1.0, END))
    f.write(text_save)
    f.close()

# 누가 만들었는지 보여주는 창을 별도로 띄우기!
def maker():
    help_view = Toplevel(window) # 따로 메시지창 띄우기용 
    help_view.geometry("300x50")
    help_view.title("만든이")
    lb = Label(help_view, text = "강윤호가 만든 메모장입니다.")
    lb.pack()

window = Tk()
window.title("Notepad")
window.geometry("400x400")
window.resizable(False, False)

menu = Menu(window)
menu_1 = Menu(menu, tearoff = 0)
menu_1.add_command(label="새파일")  # add_command : 항목에 대한 추가
menu_1.add_command(label="저장")
menu_1.add_separator()
menu_1.add_command(label="종료", command=window.destroy)
menu.add_cascade(label="파일", menu=menu_1)

menu_2 = Menu(menu, tearoff = 0)
menu_2.add_command(label="만든이")
menu.add_cascade(label="만든이", menu=menu_2)

text_area = Text(window) # 텍스트 입력창 

# 첫번째 행과 첫번째 열에 가중치를 몰빵한 후
window.grid_rowconfigure(0, weight=1)   
window.grid_columnconfigure(0, weight=1)

## 첫번째 열과 행에 배치한다(가중치?)

# 텍스트 입력창으로 가득 채운다!
text_area.grid(sticky = N + E + S + W) # 동서남북 방향에 가득 채운다.

window.config(menu=menu) # 메뉴를 창에다 추가한다!
window.mainloop()
