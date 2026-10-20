import ctypes
from ctypes import wintypes
import sys

print("--- ШАГ 1: Загрузка управляющей библиотеки kernel32.dll ---")
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

print("\n--- ШАГ 2: Ручное проецирование внешней библиотеки user32.dll в ОЗУ ---")
# КРИТИЧНО: задаём restype, иначе ctypes вернёт c_int (32 бита) и обрежет 64-битный HMODULE
kernel32.LoadLibraryW.argtypes = [wintypes.LPCWSTR]
kernel32.LoadLibraryW.restype = wintypes.HMODULE

dll_name = "user32.dll"
h_module = kernel32.LoadLibraryW(dll_name)

if not h_module:
    print(f"[ОШИБКА] Не удалось загрузить библиотеку. Код ошибки Windows: {ctypes.get_last_error()}")
    sys.exit(1)

print(f"[УСПЕХ] Библиотека {dll_name} успешно спроецирована в память Ring 3!")
print(f"[НИЗКИЙ УРОВЕНЬ] Дескриптор HMODULE (базовый адрес в ОЗУ): {hex(h_module)}")

print("\n--- ШАГ 3: Парсинг Таблицы Экспорта и поиск адреса функции ---")
kernel32.GetProcAddress.argtypes = [wintypes.HMODULE, ctypes.c_char_p]
kernel32.GetProcAddress.restype = ctypes.c_void_p

func_name = b"MessageBoxW"
func_address = kernel32.GetProcAddress(h_module, func_name)

if not func_address:
    print(f"[ОШИБКА] Функция {func_name.decode()} не найдена в Таблице Экспорта DLL!")
    print(f"Код ошибки Windows: {ctypes.get_last_error()}")
    kernel32.FreeLibrary(h_module)
    sys.exit(1)

print(f"[УСПЕХ] Функция найдена!")
print(f"[НИЗКИЙ УРОВЕНЬ] Точный виртуальный адрес кода {func_name.decode()} в ОЗУ: {hex(func_address)}")

print("\n--- ШАГ 4: Динамический вызов функции по найденному адресу ---")
# Правильный прототип MessageBoxW через wintypes:
# int MessageBoxW(HWND hWnd, LPCWSTR lpText, LPCWSTR lpCaption, UINT uType)
MessageBoxW_proto = ctypes.WINFUNCTYPE(
    wintypes.INT,      # возвращает int
    wintypes.HWND,     # hWnd
    wintypes.LPCWSTR,  # lpText
    wintypes.LPCWSTR,  # lpCaption
    wintypes.UINT      # uType
)
message_box_func = MessageBoxW_proto(func_address)

# MB_TOPMOST | MB_SETFOREGROUND — окно поверх консоли и активно
MB_TOPMOST = 0x00040000
MB_SETFOREGROUND = 0x00010000
flags = MB_TOPMOST | MB_SETFOREGROUND

print("[ПРОЦЕССОР] Выполняем переход по адресу функции (CALL)...")
result = message_box_func(
    None,
    "Сообщение вызвано через прямой адрес из Таблицы Экспорта!",
    "Системное программирование",
    flags
)
print(f"Результат вызова: {result}")
print(f"[РЕЗУЛЬТАТ] MessageBoxW вернул: {result} (0 = ошибка, 1 = нажата OK)")

print("\n--- ШАГ 5: Освобождение системных ресурсов ---")
# ИСПРАВЛЕНИЕ: Явно указываем, что FreeLibrary принимает 64-битный HMODULE
kernel32.FreeLibrary.argtypes = [wintypes.HMODULE]
kernel32.FreeLibrary.restype = wintypes.BOOL

kernel32.FreeLibrary(h_module)
print("[УСПЕХ] Модуль выгружен из памяти процесса.")