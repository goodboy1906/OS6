from colorama import init, Fore, Back
import cmd, os

init(autoreset=True)  # colorama init

MEMORY_SIZE = 256


def read_bytes(filename, start, size):
    try:
        with open(filename, 'rb') as file:
            file.seek(start, 0)
            data = file.read(size)
        return data
    except FileExistsError:
        print(Fore.RED + f"[!] ")


def create_task(name, size):
    try:
        with open(name, "wb") as task_file:
            task_file.write(bytes([65 for i in range(size)]))
        print("[+] Файл создан", name)
        return
    except Exception:
        print('[-] Ошибка. Файл не создан')


def check_for_range(first_range_max, second_range_min):
    if second_range_min - first_range_max == 1:
        return None
    if first_range_max + 1 == second_range_min - 1:
        return [second_range_min]
    return [first_range_max + 1, second_range_min - 1]


def search_ranges(size, addr_ranges):
    undistributed_addresses = []

    if len(addr_ranges) < 1:
        return [[0, size]]

    for i in range(len(addr_ranges) - 1):
        free_range = check_for_range(addr_ranges[i][1], addr_ranges[i + 1][0])
        if free_range is not None:
            undistributed_addresses.append(free_range)

    if addr_ranges[0][0] != 0:
        if addr_ranges[0][0] - 1 == 0:
            undistributed_addresses.append([0])
        else:
            undistributed_addresses.append([0, addr_ranges[0][0] - 1])
    if addr_ranges[-1][1] < size:
        if addr_ranges[-1][1] + 1 == size:
            undistributed_addresses.append([size])
        else:
            undistributed_addresses.append([addr_ranges[-1][1] + 1, size])
    return undistributed_addresses if len(undistributed_addresses) > 0 else None


def short_has_arg(opt, shortopts):
    for i in range(len(shortopts)):
        if opt == shortopts[i] != ':':
            return shortopts.startswith(':', i + 1)


def do_short(opts, args, shortopts):
    i = 0
    optargs = args[1:]
    if args[0][1:] in shortopts:
        if short_has_arg(args[0][1:], shortopts):
            while i < len(optargs) and not optargs[i].startswith('-'):
                i += 1
            if i > 0:
                opts.append((args[0], optargs[:i]))
            else:
                return None, None
        else:
            opts.append((args[0], ''))
        return opts, optargs[i:]
    return None, None


def parse(args: list, shortopts: str):
    opts = []
    while args and args[0].startswith('-') and args[0] != '-':
        opts, args = do_short(opts, args, shortopts)
    return opts, args


def pretty_table(data, cell_sep=' | ', header_separator=True) -> str:
    rows = len(data)
    cols = len(data[0])

    col_width = []
    for col in range(cols):
        columns = [str(data[row][col]) for row in range(rows)]
        col_width.append(len(max(columns, key=len)))

    separator = "-+-".join('-' * n for n in col_width)

    lines = []

    for i, row in enumerate(range(rows)):
        result = []
        for col in range(cols):
            item = str(data[row][col]).rjust(col_width[col])
            result.append(item)

        lines.append(cell_sep.join(result))

        if i == 0 and header_separator:
            lines.append(separator)

    return '\n'.join(lines)


# Низший уровень(физический)
class Memory:
    def __init__(self):
        self.__memory = [0] * MEMORY_SIZE

    # Чтение памяти по адресу и размеру
    def read(self, address, bytes_count=1):
        if address + bytes_count > MEMORY_SIZE:
            print(
                Fore.RED + f"[!] Выход за пределы адресного пространства памяти!\n"
                + f"\t\tНевозможно прочитать по адресу больше чем {Fore.LIGHTGREEN_EX + str(MEMORY_SIZE)}")
            return
        return self.__memory[address:address + bytes_count]

    # Запись в память массива байтов по адресу
    def write(self, base_address, byte_arr):
        if base_address >= MEMORY_SIZE:
            print("[!] Выход за пределы адресного пространства памяти")
            return False
        if base_address + len(byte_arr) > MEMORY_SIZE:
            print(
                Fore.RED + f"[!] Выход за пределы адресного пространства памяти!\n"
                + f"\t\tНевозможно прочитать по адресу больше чем {Fore.LIGHTGREEN_EX + str(MEMORY_SIZE)}")
            return False
        self.__memory[base_address:base_address + len(byte_arr)] = byte_arr
        return True


# Сегмент памяти процесса
class Segment:
    def __init__(self, name, start, size):
        self.name = name
        self.start = start
        self.size = size
        self.is_load = False


# Процесс(Виртуальная память представлена файлом задачи)
class Process:
    def __init__(self, name, size):
        self.name = name
        self.size = size
        self.segments_table = {}  # {"example": obj}

    # Добавление сегмента в таблицу процесса
    def add_segment(self, name, start, size):
        if sum(x.size for x in self.segments_table.values()) == self.size:
            print(Fore.LIGHTMAGENTA_EX + f"[x] Вся память процесса размечена на сегменты!")
            print('\t\t\t\t' + Fore.LIGHTYELLOW_EX + ', '.join(self.segments_table.keys()))
            return False
        if name in self.segments_table.keys():
            print(Fore.LIGHTBLUE_EX + f"[-] Имя сегмента '{Fore.LIGHTGREEN_EX + name + Fore.LIGHTBLUE_EX}' "
                                      f"для процесса '{Fore.LIGHTGREEN_EX + self.name + Fore.LIGHTBLUE_EX}' занято!")
            return False

        if size > self.size:
            print(Fore.RED + f"[-] Размер сегмента больше допустимого!")
            return False

        if start + size - 1 > self.size:
            print(
                Fore.RED + f"[!] Выход за пределы адресного пространства памяти!\n"
                + f"\t\tНевозможно писать по адресу {Fore.LIGHTGREEN_EX + str(start + size)}")
            return False

        for i in self.segments_table.values():
            if start in range(i.start + 1, i.start + i.size) or start + size in range(i.start + 1, i.start + i.size):
                print(
                    Fore.LIGHTBLUE_EX + f"[-] Вхождение в имющийся сегмент!\n"
                    + f"\t\t{Fore.LIGHTGREEN_EX} {[i.name, i.start, i.start + i.size]}")
                return False
        self.segments_table[name] = Segment(name, start, size)
        return True

    # Получить нераспределенную память процесса | НЕ ВЫГРУЖАТЬ ИЗ ПУЛА В ПАМЯТЬ ПРИ НЕ РАСПРЕД. УЧАСТКАХ!
    def get_undistributed_addresses(self):

        addr_ranges = sorted([i for i in [[x.start, x.start + x.size - 1]
                                          for x in list(self.segments_table.values())]])
        return search_ranges(self.size - 1, addr_ranges)

    # Размер всех сегментов | для контроля памяти процессф
    def _get_segments_size(self):
        return sum([i.size for i in self.segments_table.values()])

    # Получение объекта сегмента по имени
    def _get_segment(self, name):
        try:
            return self.segments_table[name]
        except KeyError:
            print(Fore.RED + f"[!] Нет сегмента с именем {Fore.LIGHTYELLOW_EX + name}")

    def table(self):
        data = []
        for name, segment_obj in self.segments_table.items():
            data.append([name, segment_obj.start, segment_obj.size, segment_obj.is_load])
        data.insert(0, ["Сегмент", "Базовый адрес", "Объем", "Загружен в память"])

        return f'Процесс {self.name}  {self.size} bytes\n{pretty_table(data)}'


# Менелжер памяти
class MemoryManager:
    def __init__(self):
        self.memory = Memory()
        self.processes_table = {}
        self.phys_memory_table = {}  # {'segment_name': [base, size]}

    # Поиск оптимальной области в физической памяти
    def __find_optimal(self, size):
        free_rng = self._free_memory_ranges()
        if free_rng is not None:
            searched = [[info[0], size] for info in free_rng if info[1] - info[0] + 1 >= size]
            return searched[0] if len(searched) else None

    # поиск совпадения в физицеской памяти
    def __find_match(self, bytes_arr, size):
        for seg_name, info in self.phys_memory_table.items():
            # найден по размеру
            if info[1] == size:
                match_bytes = bytes(self.memory.read(info[0], info[1]))
                if match_bytes == bytes_arr:
                    return seg_name, info

    # Получение процесса по имени
    def _get_process(self, name):
        try:
            return self.processes_table[name]
        except KeyError:
            print(Fore.RED + f"[!] Нет процесса с именем {Fore.LIGHTYELLOW_EX + name}")
            return

    # Получить диапозоны свободной памяти
    def _free_memory_ranges(self):
        usage_addr_ranges = sorted([i for i in [[x[0], x[0] + x[1] - 1]
                                                for x in list(self.phys_memory_table.values())]])
        usage_addr_ranges = list(dict.fromkeys([tuple(x) for x in usage_addr_ranges]))
        return search_ranges(MEMORY_SIZE - 1, usage_addr_ranges)

    # Добавить процесс(задачу) | ИМЯ ЭТО НАЗВАНИЕ ФАЙЛА
    def add_process(self, name):
        try:
            file = open(name, 'rb')
            file.close()
        except FileNotFoundError:
            print(Fore.RED + f"[!] Нет файла с именем {Fore.LIGHTYELLOW_EX + name}")
            return
        size = os.path.getsize(name)
        if size > MEMORY_SIZE - 1:
            print(
                Fore.RED + f"[!] Размер задачи выше максимального! "
                           f"{Fore.LIGHTYELLOW_EX + str(size) + Fore.RED} > {Fore.RESET + str(MEMORY_SIZE - 1)}")
            return False

        self.processes_table[name] = Process(name, size)
        return True

    # Загрузка сегмента в паямять по имени процесса и сегмента
    def load_segment(self, process_name, segment_name):
        prosess = self._get_process(process_name)
        if prosess is None:
            return False

        if prosess._get_segments_size() < prosess.size:
            print(f"{Fore.RED}[!] Не вся память процесса '{process_name}' распреределена"
                  f"\n\t{prosess.get_undistributed_addresses()}")
            return False

        segment = prosess._get_segment(segment_name)
        if segment is None:
            return False

        if segment.is_load:
            print(Fore.LIGHTBLUE_EX + f"Сегмент {Fore.LIGHTMAGENTA_EX + segment.name} "
                                      f"{Fore.LIGHTBLUE_EX}уже загружен в физическую память")
            return False

        segment_data = read_bytes(process_name, segment.start, segment.size)
        match = self.__find_match(segment_data, segment.size)

        if match:
            print(f"{Fore.LIGHTGREEN_EX}[+] Обнаружен сегмент, который уже загружен. Изменение таблицы памяти"
                  f"\n\t\t\tСегмент '{segment.name}' == сегменту '{match[0].split(', ')[1]}' "
                  f"процесса '{match[0].split(', ')[0]}'")
            self.phys_memory_table[', '.join([process_name, segment_name])] = self.phys_memory_table[match[0]]
            segment.is_load = True
            return True

        phys_addr = self.__find_optimal(segment.size)
        if phys_addr is None:
            print(Fore.RED + f"[x] В данный момент нет места для сегмента '{Fore.CYAN + segment.name}'\n")
            return False
        else:
            print(Fore.LIGHTGREEN_EX + f"[+] Успех! Выделение места для сегмента " \
                                       f"'{Fore.CYAN + segment.name + Fore.LIGHTGREEN_EX}' в физической памяти "
                                       f"{Fore.BLUE + str(phys_addr[1])} byte")

        self.phys_memory_table[', '.join([process_name, segment_name])] = phys_addr
        if self.memory.write(phys_addr[0], segment_data):
            segment.is_load = True
            print(Fore.LIGHTGREEN_EX + f"[+] Успех! Загружен в память, область "
                                       f"{Fore.CYAN + '[' + str(phys_addr[0])}:"
                                       f"{Fore.CYAN + str(phys_addr[1] + phys_addr[0] - 1)}]\n")
            return True

    # Выгрузить сегмент из памяти
    def unload_segment(self, process_name, segment_name):
        prosess = self._get_process(process_name)
        if prosess is None:
            return False

        segment = prosess._get_segment(segment_name)
        if segment is None:
            return False
        key = f'{process_name}, {segment_name}'
        relation = [i for i in self.phys_memory_table if self.phys_memory_table[i] == self.phys_memory_table[key]]
        if len(relation) > 1:
            print(f"{Fore.LIGHTGREEN_EX}[+] Сегменты {relation} разделены, {key} "
                  f"выгружается без освобождения физического диапазона...")
            self.phys_memory_table.pop(key)
            segment.is_load = False
            print(f"{Fore.LIGHTGREEN_EX}[+] Выгружен\n")
            return True
        phys_segment_area = self.phys_memory_table[key]
        print(f"{Fore.LIGHTGREEN_EX}[+] Сегмент распологается в области "
              f"[{phys_segment_area[0], phys_segment_area[0] + phys_segment_area[1] - 1}] выгружается...")
        segment.is_load = False

        if self.memory.write(self.phys_memory_table[key][0], [0 for i in range(segment.size)]):
            self.phys_memory_table.pop(key)
            segment.is_load = False
            print(f"{Fore.LIGHTGREEN_EX}[+] Выгружен\n")
            return True

        return False

    def proc_table(self):
        data = []
        for name, process_obj in self.processes_table.items():
            data.append([name, process_obj.size, len(list(process_obj.segments_table.keys())),
                         sum(i.size for i in process_obj.segments_table.values())])
        data.insert(0, ["Процесс", "Объем", "Кол-во Сегментов", "Объем сегментов"])

        return f'Таблица процессов\n{pretty_table(data)}'

    def mem_table(self):
        data = []
        for name, value in self.phys_memory_table.items():
            data.append([name, value[0], value[1]])

        usage = list(dict.fromkeys([tuple(x) for x in [i[1:] for i in data]]))
        usage = sum([i[1] for i in usage])
        data.insert(0, ["Процесс, Сегмент", "База", "Объем"])

        return f'Таблица физицеской памяти ' \
               f'|{Back.GREEN + Fore.BLACK + " " + str(MEMORY_SIZE) + " " + Back.RESET + Fore.RESET}|' \
               f'{Back.YELLOW + Fore.BLACK + " " + str(usage) + " " + Fore.RESET + Back.RESET}|\n{pretty_table(data)}'

    def hex_view(self):
        bytes, line = 0, []
        print('   ', end='')
        [print(Fore.LIGHTBLUE_EX + '{:^2} '.format(i) + Fore.RESET, end='') for i in range(16)]
        print('')
        lines = 0
        for b in self.memory.read(0, MEMORY_SIZE):
            if bytes % 16 == 0:
                print(Fore.LIGHTGREEN_EX + '{:^2}'.format(str(lines)) + Fore.RESET, end=' ')
            bytes += 1
            line.append(b)
            print('{:02X}'.format(b), end=' ')
            if bytes % 16 == 0:
                print("|", end='')
                for b2 in line:
                    if b2 != 0:
                        if 32 <= b2 <= 126:
                            print(chr(b2), end='')
                        else:
                            print(Back.LIGHTBLACK_EX + ".", end='')
                    else:
                        print(Back.LIGHTBLACK_EX + " ", end='')
                line = []
                lines += 1
                print('')


class ManagerShell(cmd.Cmd):
    intro = f"{__doc__}\n\n\tДобро пожаловать в интерпритатор команд Менеджера Памяти.\n\t\tВведите help или ? для " \
            f"получения информации\n"
    prompt = f'[{Fore.CYAN + str(MEMORY_SIZE)}b{Back.RESET + Fore.RESET}]{Fore.LIGHTYELLOW_EX} ' \
             f'(manager){Fore.GREEN} & '
    file = None
    ruler = '-'
    doc_header = "Задокументированные команды (введите help <command>):"
    use_rawinput = False

    def __init__(self, manager: MemoryManager):
        super().__init__()
        self.manager = manager

    def default(self, line):
        self.stdout.write(Fore.RED + '[-] Неверная команда: %s\n' % line)

    def do_create(self, args, shortopts='n:s:'):
        opts, args = parse(args.split(), shortopts)
        if opts and not args:
            opts = {i[0]: i[1] for i in opts}
            if not '-n' in opts.keys():
                print("Необходимо название -n name")
                return
            if not '-s' in opts.keys():
                print("Необходим вес -s size")
                return
            if len(opts['-s']) > 1:
                print("Переданы лишние аргументы -s")
                return

            if not opts['-s'][0].isdigit():
                print("Неверный тип для -s. Введите одно число")
                return
            create_task(''.join(opts['-n']), int(opts['-s'][0]))
            return
        print(f"[{Fore.RED}*{Fore.RESET}] Необходимы обязательые аргументы")
        self.help_create()

    def help_create(self):
        print(f"Создание файла с определенным весом [-n] {Fore.RED}name{Fore.RESET} "
              f"[-s] {Fore.RED}size{Fore.RESET}\nПримеры: "
              f"\n\tcreate -n task -s 64")

    def do_add(self, args, shortopts='p:s:'):
        opts, args = parse(args.split(), shortopts)
        if opts and not args:
            opts = {i[0]: i[1] for i in opts}
            if not '-p' in opts.keys():
                print("Необходимо название процесса -p processname")
                return
            if not '-s' in opts.keys():
                if self.manager.add_process(''.join(opts['-p'])):
                    print(Fore.LIGHTGREEN_EX + "[+] Процесс добавлен")
                return
            else:
                process = self.manager._get_process(''.join(opts['-p']))
                if process:
                    if len(opts['-s']) % 3 == 0:
                        segments_params = [opts['-s'][i:i + 3] for i in range(0, len(opts['-s']), 3)]
                        for i in segments_params:
                            if not i[1].isdigit() and not i[2].isdigit():
                                print(f"Неверный тип данных для информации о сегментах {i}\n Пример -s str int int")
                            else:
                                if process.add_segment(i[0], int(i[1]), int(i[2])):
                                    print(Fore.LIGHTGREEN_EX + "[+] Сегмент добавлен", i[0], int(i[1]), int(i[2]))
                    else:
                        print("Лишняя информация о сегментах ", *opts['-s'][len(opts['-s']) // 3 * 3:])
            return
        print(f"[{Fore.RED}*{Fore.RESET}] Необходимы обязательые аргументы")
        self.help_add()

    def help_add(self):
        print(f"Добавление процесса и сегментов в менеджер [-p] {Fore.RED}processname{Fore.RESET} "
              f"[-s] {Fore.CYAN}name, base, size{Fore.RESET}\nПримеры: "
              f"\n\tadd -p processname\n\tadd -p processname -s A 0 64")

    def do_table(self, args, shortopts='p:'):
        """Вывод таблиц table [-p] [mem] [proc] [hex].\nПримеры:\n\ttable -p processname - таблица сегментов процесса
        \r\ttable mem - таблица физической памяти\n\ttable proc - таблица процессов\n\ttable hex"""
        opts, args = parse(args.split(), shortopts)
        if opts and not args:
            opts = {i[0]: i[1] for i in opts}
            process = self.manager._get_process(''.join(opts['-p']))
            if process:
                print('\n' + process.table() + '\n')
            return
        if not opts and args:
            if 'mem' == ''.join(args):
                print('\n' + self.manager.mem_table() + '\n')
            elif 'proc' == ''.join(args):
                print('\n' + self.manager.proc_table() + '\n')
            elif 'hex' == ''.join(args):
                self.manager.hex_view()
            return
        print(f"[{Fore.RED}*{Fore.RESET}] Необходимы обязательые аргументы")
        self.do_help('table')

    def do_load(self, args, shortopts='p:s:'):
        """Загрузить сегмент в память [-p] processname [-s] name.\nПримеры:
        \r\tload -p process name -s segment name - загрузить в память сегмент определенного процесса"""
        opts, args = parse(args.split(), shortopts)
        if opts and not args:
            opts = {i[0]: i[1] for i in opts}
            if not '-p' in opts.keys():
                print("Необходим аргумент -p")
                return
            elif not '-s' in opts.keys():
                print("Необходим аргумент -s")
                return
            else:
                self.manager.load_segment(''.join(opts['-p']), ''.join(opts['-s']))
            return
        print(f"[{Fore.RED}*{Fore.RESET}] Необходимы обязательые аргументы")
        self.help_load()

    def help_load(self):
        print(f"Загрузить сегмент в память [-p] {Fore.RED}processname{Fore.RESET} [-s] {Fore.RED}name{Fore.RESET}."
              f"\nПримеры:\n\tload -p process name -s segment name - загрузить в память сегмент определенного процесса")

    def help_unload(self):
        print(f"Выгрузить сегмент из памяти [-p] {Fore.RED}processname{Fore.RESET} [-s] {Fore.RED}name{Fore.RESET}."
              f"\nПримеры:\n\tunload -p process name -s segment name - выгрузить из памяти сегмент определенного "
              f"процесса")

    def do_unload(self, args):
        shortopts = 'p:s:'
        opts, args = parse(args.split(), shortopts)
        if opts and not args:
            opts = {i[0]: i[1] for i in opts}
            if not '-p' in opts.keys():
                print("Необходим аргумент -p")
                return
            elif not '-s' in opts.keys():
                print("Необходим аргумент -s")
                return
            else:
                self.manager.unload_segment(''.join(opts['-p']), ''.join(opts['-s']))
            return
        print(f"[{Fore.RED}*{Fore.RESET}] Необходимы обязательые аргументы")
        self.help_unload()


cli = ManagerShell(MemoryManager())

os.system('cls' if os.name == 'nt' else 'clear')
cli.cmdloop()
