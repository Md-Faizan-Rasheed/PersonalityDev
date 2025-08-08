import threading
import time


def func():
    print('ran')
    time.sleep(1)
    print("done")


# creating thread object 
x = threading.Thread(target=func)

x.start()
print(threading.active_count())

