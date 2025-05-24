import os
import platform
import time

def hay_conexion():
    sistema = platform.system().lower()
    comando = "ping -c 1 google.com" if "linux" in sistema or "darwin" in sistema else "ping -n 1 google.com"
    return os.system(comando) == 0

def pitido():
    sistema = platform.system().lower()
    if "windows" in sistema:
        import winsound
        winsound.Beep(1000, 500)
    else:
        print("\a")

def esperar_conexion():
    print("Esperando conexión a internet")
    intento = 1
    while True:
        print(f"Intento {intento}")
        if hay_conexion():
            print("Conexion detectada")
            for _ in range(1):
                pitido()
            break
        intento += 1
        time.sleep(10)

if __name__ == "__main__":
    esperar_conexion()