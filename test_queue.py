import queue, threading, pyttsx3, time

engine = pyttsx3.init()
tts_queue = queue.Queue()

def tts_worker():
    while True:
        txt = tts_queue.get()
        print("SPEAK:", txt)
        engine.say(txt)
        engine.runAndWait()
        tts_queue.task_done()

threading.Thread(target=tts_worker, daemon=True).start()

tts_queue.put("Queue test: Hello this is working.")
time.sleep(5)
print("Done")
