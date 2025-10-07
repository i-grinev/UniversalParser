import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.action_chains import ActionChains
try:
    from webdriver_manager.chrome import ChromeDriverManager
    HAS_WEBDRIVER_MANAGER = True
except ImportError:
    HAS_WEBDRIVER_MANAGER = False
import pandas as pd
import json
import time
import threading
import os
from urllib.parse import urljoin, urlparse
import logging
import random
import re


class UniversalParser:
    def __init__(self, root):
        self.root = root
        self.root.title("Универсальный Парсер v1.5")
        self.root.geometry("1400x900")
        self.root.configure(bg='#f0f0f0')
        # Настройка браузера
        self.driver = None
        self.waiting_for_restart = False
        self.setup_driver()
        # Переменные для хранения данных
        self.selected_elements = []
        self.click_elements = []  # Элементы для клика (selectors)
        self.links = []
        self.results = []
        self.is_selecting = False
        self.is_click_selecting = False
        self.parsing_in_progress = False
        self.total_links = 0
        self.page_limit = 0  # Лимит страниц
        self.temp_results_file = 'temp_results.json'
        self.load_temp_results()  # Загрузка временных результатов при запуске
        self.setup_ui()
        self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger()

    def load_temp_results(self):
        """Загрузка временных результатов"""
        if os.path.exists(self.temp_results_file):
            try:
                with open(self.temp_results_file, 'r', encoding='utf-8') as f:
                    self.results = json.load(f)
                print(f"Загружено {len(self.results)} временных результатов")
            except Exception as e:
                print(f"Ошибка загрузки временных результатов: {e}")
                self.results = []

    def save_temp_results(self):
        """Сохранение результатов после каждой ссылки"""
        try:
            with open(self.temp_results_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
            print(f"Сохранено {len(self.results)} результатов")
        except Exception as e:
            print(f"Ошибка сохранения временных результатов: {e}")

    def setup_driver(self):
        """Настройка Chrome драйвера с ВИДИМЫМ браузером"""
        try:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
            chrome_options = Options()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            chrome_options.add_argument("--disable-features=VizDisplayCompositor")
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-backgrounding-occluded-windows")
            chrome_options.add_argument("--disable-renderer-backgrounding")
            chrome_options.add_argument("--window-size=1200,800")
            chrome_options.add_argument("--start-maximized")
            if HAS_WEBDRIVER_MANAGER:
                service = Service(ChromeDriverManager().install())
            else:
                service = Service()  # Предполагается, что chromedriver в PATH
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            print("Браузер запущен с улучшенными настройками")
        except Exception as e:
            error_msg = f"Не удалось запустить браузер: {str(e)}\nЕсли ошибка связана с chromedriver, установите webdriver_manager: pip install webdriver-manager\nИли скачайте chromedriver и добавьте в PATH."
            messagebox.showerror("Ошибка", error_msg)

    def restart_driver(self):
        """Перезапуск браузера в основном потоке"""
        self.waiting_for_restart = True
        try:
            if self.driver:
                self.driver.quit()
                print("Браузер закрыт")
            time.sleep(2)
            self.setup_driver()
            print("Браузер перезапущен")
        except Exception as e:
            print(f"Ошибка перезапуска браузера: {e}")
        finally:
            self.waiting_for_restart = False

    def angular_click(self, element, description=""):
        """Клик для AngularJS элементов"""
        try:
            angular_ready = self.driver.execute_script("return typeof angular !== 'undefined' && angular.element")
            if angular_ready:
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                time.sleep(0.5)
                self.driver.execute_script("angular.element(arguments[0]).triggerHandler('click');", element)
                print(f"  ✓ AngularJS triggerHandler клик успешен: {description}")
                time.sleep(1)
                return True
            else:
                print(f"  ! AngularJS не доступен: {description}")
                return False
        except Exception as e:
            print(f"  ! AngularJS клик не сработал: {e}")
            return False

    def smart_click(self, element, description=""):
        """Улучшенный умный клик с поддержкой AngularJS"""
        try:
            print(f"  Пытаюсь кликнуть: {description}")
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            time.sleep(0.5)
            WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(element))
            if self.angular_click(element, description):
                return True
            try:
                element.click()
                print(f"  ✓ Обычный клик успешен: {description}")
                return True
            except ElementClickInterceptedException:
                pass
            try:
                self.driver.execute_script("arguments[0].click();", element)
                print(f"  ✓ JavaScript клик успешен: {description}")
                return True
            except Exception as e:
                print(f"  ! JavaScript клик не сработал: {e}")
            try:
                actions = ActionChains(self.driver)
                actions.move_to_element(element).pause(0.5).click().perform()
                print(f"  ✓ ActionChains клик успешен: {description}")
                return True
            except Exception as e:
                print(f"  ! ActionChains клик не сработал: {e}")
            try:
                location = element.location_once_scrolled_into_view
                size = element.size
                x = location['x'] + size['width'] // 2
                y = location['y'] + size['height'] // 2
                self.driver.execute_script(f"window.scrollTo(0, {y - 100});")
                time.sleep(0.5)
                self.driver.execute_script(f"document.elementFromPoint({x}, {y}).click();")
                print(f"  ✓ Клик по координатам успешен: {description}")
                return True
            except Exception as e:
                print(f"  ! Клик по координатам не сработал: {e}")
            print(f"  ! Все способы клика не сработали: {description}")
            return False
        except TimeoutException:
            print(f"  ! Таймаут ожидания кликабельности: {description}")
            return False
        except Exception as e:
            print(f"  ✗ Ошибка при клике {description}: {e}")
            return False

    def wait_for_element(self, selector, timeout=10):
        """Ожидание появления элемента"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            return element
        except TimeoutException:
            print(f"  Элемент не появился: {selector}")
            return None

    def extract_phone_numbers(self, text):
        """Извлечение телефонных номеров из текста"""
        patterns = [
            r'\+7\s?\(?\d{3}\)?\s?\d{3}[\s-]?\d{2}[\s-]?\d{2}',
            r'8\s?\(?\d{3}\)?\s?\d{3}[\s-]?\d{2}[\s-]?\d{2}',
            r'\+7-\d{3}-\d{3}-\d{2}-\d{2}',
            r'\d{3}[\s-]?\d{2}[\s-]?\d{2}[\s-]?\d{2}',
        ]
        phones = []
        for pattern in patterns:
            found = re.findall(pattern, text)
            phones.extend(found)
        return list(set(phones))

    def setup_ui(self):
        """Настройка пользовательского интерфейса"""
        # Стиль — сохраняем как атрибут класса
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('TNotebook', background='#f0f0f0')
        self.style.configure('TNotebook.Tab', padding=[20, 8], font=('Arial', 12, 'bold'))
        self.style.configure('Header.TLabel', font=('Arial', 14, 'bold'), foreground='#2c3e50')
        self.style.configure('Info.TLabel', font=('Arial', 10), foreground='#7f8c8d')

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.setup_links_tab(notebook)
        self.setup_selection_tab(notebook)
        self.setup_results_tab(notebook)
        self.setup_progress_panel()

    def setup_progress_panel(self):
        """Панель прогресса внизу окна"""
        progress_frame = ttk.Frame(self.root, relief=tk.RAISED, borderwidth=1)
        progress_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)
        progress_frame.configure(style='TFrame')

        self.status_var = tk.StringVar(value="Готов к работе")
        status_label = ttk.Label(progress_frame, textvariable=self.status_var, font=('Arial', 11, 'bold'), foreground='#2c3e50')
        status_label.pack(anchor=tk.W, pady=(0,5))

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            length=1360,
            mode='determinate',
            style='green.Horizontal.TProgressbar'
        )
        self.progress_bar.pack(fill=tk.X, pady=(0,5))

        # ИСПРАВЛЕНО: используем self.style
        self.style.configure('green.Horizontal.TProgressbar', background='#27ae60')

        self.progress_info_var = tk.StringVar()
        info_label = ttk.Label(progress_frame, textvariable=self.progress_info_var, font=('Arial', 9), foreground='#34495e')
        info_label.pack(anchor=tk.W)

    def setup_links_tab(self, notebook):
        """Вкладка для загрузки ссылок"""
        links_frame = ttk.Frame(notebook, padding=10)
        notebook.add(links_frame, text="1. 📎 Загрузка ссылок")

        header = ttk.Label(links_frame, text="Загрузите файл со списком ссылок (каждая ссылка с новой строки)", style='Header.TLabel')
        header.pack(pady=10)

        ttk.Label(links_frame, text="Загруженные ссылки:", style='Info.TLabel').pack(pady=5, anchor=tk.W)
        self.links_text = scrolledtext.ScrolledText(links_frame, height=15, state=tk.DISABLED, wrap=tk.WORD, font=('Consolas', 9))
        self.links_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        settings_frame = ttk.LabelFrame(links_frame, text="⚙️ Настройки парсинга", padding=10)
        settings_frame.pack(fill=tk.X, padx=5, pady=10)

        settings_inner = ttk.Frame(settings_frame)
        settings_inner.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(settings_inner, text="Лимит страниц (0 = без лимита):").pack(side=tk.LEFT)
        self.limit_var = tk.StringVar(value="0")
        self.limit_entry = ttk.Entry(settings_inner, textvariable=self.limit_var, width=10, font=('Arial', 10))
        self.limit_entry.pack(side=tk.LEFT, padx=5)

        ttk.Label(settings_inner, text="Перезапуск браузера через (страниц):").pack(side=tk.LEFT, padx=(20,0))
        self.restart_var = tk.StringVar(value="20")
        self.restart_entry = ttk.Entry(settings_inner, textvariable=self.restart_var, width=10, font=('Arial', 10))
        self.restart_entry.pack(side=tk.LEFT, padx=5)

        button_frame = ttk.Frame(links_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=10)
        ttk.Button(button_frame, text="📁 Загрузить из файла", command=self.load_links_from_file, style='Accent.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🗑️ Очистить список", command=self.clear_links, style='Stop.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="💾 Сохранить ссылки", command=self.save_links, style='Click.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🔄 Перезапустить браузер", command=self.restart_driver, style='Click.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="➡️ Далее", command=lambda: notebook.select(1), style='Accent.TButton').pack(side=tk.RIGHT, padx=5)

    def setup_selection_tab(self, notebook):
        """Вкладка для выбора данных"""
        selection_frame = ttk.Frame(notebook, padding=10)
        notebook.add(selection_frame, text="2. 🎯 Выбор данных")

        url_frame = ttk.Frame(selection_frame)
        url_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(url_frame, text="URL для предпросмотра:", style='Info.TLabel').pack(side=tk.LEFT)
        self.preview_url = ttk.Entry(url_frame, width=60, state='readonly', font=('Arial', 10))
        self.preview_url.pack(side=tk.LEFT, padx=5)
        ttk.Button(url_frame, text="🔄 Загрузить первую ссылку", command=self.load_first_link, style='Accent.TButton').pack(side=tk.LEFT, padx=5)

        content_frame = ttk.Frame(selection_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        left_frame = ttk.Frame(content_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        browser_frame = ttk.LabelFrame(left_frame, text="🌐 Управление браузером", padding=10)
        browser_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        browser_controls = ttk.Frame(browser_frame)
        browser_controls.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(browser_controls, text="🎯 ВЫБРАТЬ ДАННЫЕ ДЛЯ ПАРСИНГА", 
                  command=self.toggle_element_selection, style="Accent.TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(browser_controls, text="🖱️ ВЫБРАТЬ КНОПКИ ДЛЯ КЛИКА", 
                  command=self.toggle_click_selection, style="Click.TButton").pack(side=tk.LEFT, padx=5)
        self.selection_status = ttk.Label(browser_controls, text="Режим: ВЫКЛ", foreground="red", font=('Arial', 10, 'bold'))
        self.selection_status.pack(side=tk.RIGHT, padx=5)

        instruction_text = """
        ВАЖНО ДЛЯ СБОРА ТЕЛЕФОНОВ (AngularJS сайты):
        1. Сначала ВЫБЕРИТЕ КНОПКИ ДЛЯ КЛИКА:
           - Кнопка "Показать телефон" (a[data-ng-click*="showPhones"])
           - Кнопка "Раскрыть контакты"
        2. Затем ВЫБЕРИТЕ ДАННЫЕ ДЛЯ ПАРСИНГА:
           - Элементы с телефонными номерами (li.ng-binding)
           - Названия, цены, описания
        Программа использует AngularJS triggerHandler для кликов!
        """
        info_label = ttk.Label(browser_frame, text=instruction_text, justify=tk.LEFT, foreground="green", font=('Arial', 9))
        info_label.pack(fill=tk.X, padx=5, pady=10)

        self.page_info = ttk.Label(browser_frame, text="Страница не загружена", wraplength=600, style='Info.TLabel')
        self.page_info.pack(fill=tk.X, padx=5, pady=2)

        right_frame = ttk.Frame(content_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5)

        click_frame = ttk.LabelFrame(right_frame, text="🖱️ Элементы для клика", padding=5)
        click_frame.pack(fill=tk.X, pady=5)
        self.click_listbox = tk.Listbox(click_frame, height=6, font=('Consolas', 9))
        self.click_listbox.pack(fill=tk.X, padx=5, pady=5)
        click_btn_frame = ttk.Frame(click_frame)
        click_btn_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(click_btn_frame, text="❌ Удалить", command=self.remove_click_element, style='Stop.TButton').pack(side=tk.LEFT)
        ttk.Button(click_btn_frame, text="🗑️ Очистить", command=self.clear_click_elements, style='Stop.TButton').pack(side=tk.RIGHT)

        parse_frame = ttk.LabelFrame(right_frame, text="📊 Элементы для парсинга", padding=5)
        parse_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.parse_listbox = tk.Listbox(parse_frame, height=10, font=('Consolas', 9))
        self.parse_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        parse_btn_frame = ttk.Frame(parse_frame)
        parse_btn_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(parse_btn_frame, text="❌ Удалить", command=self.remove_parse_element, style='Stop.TButton').pack(side=tk.LEFT)
        ttk.Button(parse_btn_frame, text="🗑️ Очистить", command=self.clear_parse_elements, style='Stop.TButton').pack(side=tk.RIGHT)

        self.start_parsing_btn = ttk.Button(right_frame, text="🚀 НАЧАТЬ ПАРСИНГ", 
                                          command=self.start_parsing, style="Accent.TButton")
        self.start_parsing_btn.pack(fill=tk.X, pady=10)
        self.stop_parsing_btn = ttk.Button(right_frame, text="⏹️ ОСТАНОВИТЬ", 
                                         command=self.stop_parsing, style="Stop.TButton")
        self.stop_parsing_btn.pack(fill=tk.X, pady=5)
        self.stop_parsing_btn.config(state=tk.DISABLED)

    def setup_results_tab(self, notebook):
        """Вкладка для отображения результатов"""
        results_frame = ttk.Frame(notebook, padding=10)
        notebook.add(results_frame, text="3. 📈 Результаты")

        header = ttk.Label(results_frame, text="Результаты парсинга", style='Header.TLabel')
        header.pack(pady=(0,10))

        tree_frame = ttk.Frame(results_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        self.results_tree = ttk.Treeview(tree_frame, show='headings', height=20)
        tree_scroll_y = ttk.Scrollbar(tree_frame, orient="vertical", command=self.results_tree.yview)
        tree_scroll_x = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.results_tree.xview)
        self.results_tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        export_frame = ttk.Frame(results_frame)
        export_frame.pack(fill=tk.X, pady=10)
        ttk.Button(export_frame, text="📊 Экспорт в Excel", command=self.export_excel, style='Accent.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(export_frame, text="📄 Экспорт в JSON", command=self.export_json, style='Click.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(export_frame, text="💾 Сохранить временные результаты", command=self.save_temp_results, style='Click.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(export_frame, text="🧹 Очистить", command=self.clear_results, style='Stop.TButton').pack(side=tk.RIGHT, padx=5)

        if self.results:
            self._display_results()

    def update_progress(self, current, total, status=""):
        """Обновление прогресса"""
        try:
            if total > 0:
                progress_percent = (current / total) * 100
                self.progress_var.set(progress_percent)
            self.status_var.set(f"Обработано: {current}/{total} {status}")
            if current == total:
                self.progress_info_var.set("Завершено! ✅")
            else:
                remaining = total - current
                self.progress_info_var.set(f"Осталось: {remaining} страниц | {status}")
            self.root.update_idletasks()
            self.root.update()
        except Exception as e:
            print(f"Ошибка обновления прогресса: {e}")

    def toggle_element_selection(self):
        if not self.driver:
            messagebox.showwarning("Предупреждение", "Сначала загрузите страницу")
            return
        if self.is_click_selecting:
            messagebox.showwarning("Предупреждение", "Сначала завершите выбор элементов для клика")
            return
        self.is_selecting = not self.is_selecting
        if self.is_selecting:
            self.selection_status.config(text="Режим: ВЫБОР ДАННЫХ", foreground="green")
            messagebox.showinfo("Режим выбора данных", 
                              "Выберите элементы ДЛЯ ПАРСИНГА (текст, цены, названия)\n"
                              "Кликайте на элементы которые нужно извлекать")
            self.setup_element_selection("parse")
        else:
            self.selection_status.config(text="Режим: ВЫКЛ", foreground="red")
            self.disable_element_selection()

    def toggle_click_selection(self):
        if not self.driver:
            messagebox.showwarning("Предупреждение", "Сначала загрузите страницу")
            return
        if self.is_selecting:
            messagebox.showwarning("Предупреждение", "Сначала завершите выбор элементов для парсинга")
            return
        self.is_click_selecting = not self.is_click_selecting
        if self.is_click_selecting:
            self.selection_status.config(text="Режим: ВЫБОР КНОПОК", foreground="blue")
            messagebox.showinfo("Режим выбора кнопок", 
                              "Выберите элементы ДЛЯ КЛИКА (кнопки, ссылки)\n"
                              "Кликайте на элементы которые нужно нажимать на каждой странице (поддержка AngularJS)")
            self.setup_element_selection("click")
        else:
            self.selection_status.config(text="Режим: ВЫКЛ", foreground="red")
            self.disable_element_selection()

    def setup_element_selection(self, mode):
        try:
            script = """
            if (window.parserHandlers) {
                document.removeEventListener('mouseover', window.parserHandlers.mouseOver);
                document.removeEventListener('mouseout', window.parserHandlers.mouseOut);
                document.removeEventListener('click', window.parserHandlers.click);
            }
            window.selectedElements = [];
            window.parserHandlers = {
                mouseOver: function(e) {
                    if (window.parserSelecting) {
                        e.target.style.outline = '2px solid blue';
                        e.target.style.cursor = 'crosshair';
                        e.stopPropagation();
                    }
                },
                mouseOut: function(e) {
                    if (window.parserSelecting && !window.selectedElements.includes(e.target)) {
                        e.target.style.outline = '';
                    }
                },
                click: function(e) {
                    if (window.parserSelecting) {
                        e.preventDefault();
                        e.stopPropagation();
                        window.selectedElements.forEach(function(el) {
                            el.style.outline = '';
                        });
                        window.selectedElements = [];
                        e.target.style.outline = '3px solid red';
                        e.target.style.backgroundColor = 'rgba(255,255,0,0.3)';
                        window.selectedElements.push(e.target);
                        var element = e.target;
                        var info = {
                            tag: element.tagName.toLowerCase(),
                            id: element.id || '',
                            classes: element.className || '',
                            text: element.textContent.trim().substring(0, 100),
                            html: element.outerHTML.substring(0, 200)
                        };
                        var selector = element.tagName.toLowerCase();
                        if (element.id) {
                            selector = '#' + element.id;
                        } else if (element.className) {
                            var classes = element.className.split(' ')
                                .filter(function(c) { return c.trim(); })
                                .join('.');
                            if (classes) selector = '.' + classes;
                        }
                        info.selector = selector;
                        info.mode = window.parserMode;
                        window.parserLastSelected = info;
                        return false;
                    }
                }
            };
            document.addEventListener('mouseover', window.parserHandlers.mouseOver, true);
            document.addEventListener('mouseout', window.parserHandlers.mouseOut, true);
            document.addEventListener('click', window.parserHandlers.click, true);
            window.parserSelecting = true;
            window.parserMode = '%s';
            """ % mode
            self.driver.execute_script(script)
            threading.Thread(target=self._check_selected_elements, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось настроить выбор элементов: {str(e)}")

    def _check_selected_elements(self):
        while self.is_selecting or self.is_click_selecting:
            try:
                selected_info = self.driver.execute_script("return window.parserLastSelected;")
                if selected_info:
                    self.driver.execute_script("window.parserLastSelected = null;")
                    self.root.after(0, self._add_selected_element, selected_info)
                time.sleep(0.3)
            except:
                time.sleep(0.3)

    def _add_selected_element(self, element_info):
        selector = element_info['selector']
        text_preview = element_info['text']
        mode = element_info['mode']
        base_name = element_info['tag']
        if element_info['id']:
            base_name = element_info['id']
        elif element_info['classes']:
            base_name = element_info['classes'].split(' ')[0]
        name = simpledialog.askstring(
            "Название поля", 
            f"Введите название для этого элемента ({'клик' if mode == 'click' else 'данные'}):\nСелектор: {selector}\nТекст: {text_preview}",
            initialvalue=base_name
        )
        if name:
            if mode == "click":
                self.click_elements.append({"name": name, "selector": selector})
                self.click_listbox.insert(tk.END, f"{name}: {selector}")
                messagebox.showinfo("Успех", f"Добавлен элемент для клика: {name}")
            else:
                self.selected_elements.append({"name": name, "selector": selector})
                self.parse_listbox.insert(tk.END, f"{name}: {selector}")
                messagebox.showinfo("Успех", f"Добавлен элемент для парсинга: {name}")

    def disable_element_selection(self):
        try:
            self.driver.execute_script("""
                window.parserSelecting = false;
                if (window.selectedElements) {
                    window.selectedElements.forEach(function(el) {
                        el.style.outline = '';
                        el.style.backgroundColor = '';
                    });
                }
            """)
            self.is_selecting = False
            self.is_click_selecting = False
        except Exception as e:
            print(f"Ошибка при отключении выбора: {e}")

    def remove_click_element(self):
        selection = self.click_listbox.curselection()
        if selection:
            index = selection[0]
            self.click_listbox.delete(index)
            self.click_elements.pop(index)

    def remove_parse_element(self):
        selection = self.parse_listbox.curselection()
        if selection:
            index = selection[0]
            self.parse_listbox.delete(index)
            self.selected_elements.pop(index)

    def clear_click_elements(self):
        self.click_listbox.delete(0, tk.END)
        self.click_elements.clear()

    def clear_parse_elements(self):
        self.parse_listbox.delete(0, tk.END)
        self.selected_elements.clear()

    def load_links_from_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    links = file.readlines()
                self.links_text.config(state=tk.NORMAL)
                self.links_text.delete(1.0, tk.END)
                for link in links:
                    if link.strip():
                        self.links_text.insert(tk.END, link.strip() + '\n')
                self.links_text.config(state=tk.DISABLED)
                messagebox.showinfo("Успех", f"Загружено {len([l for l in links if l.strip()])} ссылок")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось загрузить файл: {str(e)}")

    def clear_links(self):
        self.links_text.config(state=tk.NORMAL)
        self.links_text.delete(1.0, tk.END)
        self.links_text.config(state=tk.DISABLED)
        self.preview_url.config(state=tk.NORMAL)
        self.preview_url.delete(0, tk.END)
        self.preview_url.config(state='readonly')

    def save_links(self):
        links_text = self.links_text.get(1.0, tk.END).strip()
        if not links_text:
            messagebox.showwarning("Предупреждение", "Нет ссылок для сохранения")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(links_text)
                messagebox.showinfo("Успех", "Ссылки сохранены")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {str(e)}")

    def load_first_link(self):
        links_text = self.links_text.get(1.0, tk.END).strip()
        links = [link.strip() for link in links_text.split('\n') if link.strip()]
        if not links:
            messagebox.showwarning("Предупреждение", "Сначала загрузите файл со ссылками")
            return
        first_link = links[0]
        self.preview_url.config(state=tk.NORMAL)
        self.preview_url.delete(0, tk.END)
        self.preview_url.insert(0, first_link)
        self.preview_url.config(state='readonly')
        self.load_preview()

    def load_preview(self):
        url = self.preview_url.get().strip()
        if not url:
            messagebox.showwarning("Предупреждение", "Нет URL для загрузки")
            return
        if not self.driver:
            messagebox.showerror("Ошибка", "Браузер не запущен. Перезапустите приложение.")
            return
        self.status_var.set("Загрузка страницы...")
        self.progress_var.set(0)
        threading.Thread(target=self._load_preview_thread, args=(url,), daemon=True).start()

    def _load_preview_thread(self, url):
        try:
            if self.driver:
                self.driver.get(url)
                WebDriverWait(self.driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                current_url = self.driver.current_url
                title = self.driver.title
                self.root.after(0, lambda: self.page_info.config(
                    text=f"Страница загружена: {current_url}\nЗаголовок: {title}"
                ))
                self.root.after(0, lambda: self.status_var.set("Страница загружена"))
                self.root.after(0, lambda: self.progress_var.set(100))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Ошибка", f"Не удалось загрузить страницу: {str(e)}"))
            self.root.after(0, lambda: self.status_var.set("Ошибка загрузки"))
            self.root.after(0, lambda: self.page_info.config(text="Ошибка загрузки страницы"))

    def start_parsing(self):
        links_text = self.links_text.get(1.0, tk.END).strip()
        self.links = [link.strip() for link in links_text.split('\n') if link.strip()]
        if not self.links:
            messagebox.showwarning("Предупреждение", "Нет ссылок для парсинга")
            return
        if not self.selected_elements:
            messagebox.showwarning("Предупреждение", "Не выбраны элементы для парсинга")
            return
        if not self.driver:
            messagebox.showerror("Ошибка", "Браузер не запущен. Перезапустите приложение.")
            return
        try:
            page_limit = int(self.limit_var.get() or 0)
            restart_interval = int(self.restart_var.get() or 0)
        except ValueError:
            messagebox.showerror("Ошибка", "Введите корректные числовые значения в настройки")
            return
        if page_limit > 0:
            self.links = self.links[:page_limit]
        self.results = []
        if os.path.exists(self.temp_results_file):
            os.remove(self.temp_results_file)
        self.parsing_in_progress = True
        self.start_parsing_btn.config(state=tk.DISABLED)
        self.stop_parsing_btn.config(state=tk.NORMAL)
        self.total_links = len(self.links)
        self.status_var.set("Начало парсинга...")
        self.progress_var.set(0)
        self.progress_info_var.set("Начинаем...")
        threading.Thread(target=self._parse_all_links, args=(restart_interval,), daemon=True).start()

    def stop_parsing(self):
        self.parsing_in_progress = False
        self.start_parsing_btn.config(state=tk.NORMAL)
        self.stop_parsing_btn.config(state=tk.DISABLED)
        self.status_var.set("Парсинг остановлен")

    def _parse_all_links(self, restart_interval):
        total_links = len(self.links)
        pages_since_restart = 0
        for i, url in enumerate(self.links):
            if not self.parsing_in_progress:
                break
            short_url = url[:50] + "..." if len(url) > 50 else url
            try:
                if restart_interval > 0 and pages_since_restart >= restart_interval:
                    print(f"Перезапуск браузера после {pages_since_restart} страниц")
                    self.root.after(0, lambda: self.status_var.set("Перезапуск браузера..."))
                    self.root.after(0, self.restart_driver)
                    while self.waiting_for_restart:
                        time.sleep(0.5)
                    pages_since_restart = 0
                    time.sleep(2)

                print(f"\n=== Обрабатывается {i+1}/{total_links}: {url} ===")
                self.driver.get(url)
                WebDriverWait(self.driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                time.sleep(random.uniform(1, 3))

                if self.click_elements:
                    print(f"  Выполняю клики по {len(self.click_elements)} типам элементов")
                    for click_element in self.click_elements:
                        try:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, click_element["selector"])
                            print(f"    Найдено {len(elements)} элементов для: {click_element['name']}")
                            clicked_count = 0
                            for idx, elem in enumerate(elements):
                                if self.smart_click(elem, f"{click_element['name']} #{idx+1}"):
                                    clicked_count += 1
                                    time.sleep(random.uniform(2, 4))
                                else:
                                    print(f"      ✗ Не удалось кликнуть: {click_element['name']} #{idx+1}")
                            print(f"    ✓ Успешно кликнуто: {clicked_count}/{len(elements)} для {click_element['name']}")
                        except Exception as e:
                            print(f"    ✗ Ошибка при клике {click_element['name']}: {e}")

                time.sleep(random.uniform(2, 3))

                page_data = {"url": url}
                html_content = self.driver.page_source
                soup = BeautifulSoup(html_content, 'html.parser')
                for element in self.selected_elements:
                    try:
                        selected_elements = soup.select(element["selector"])
                        if selected_elements:
                            texts = [elem.get_text(strip=True) for elem in selected_elements]
                            page_data[element["name"]] = " | ".join(texts)
                        else:
                            page_data[element["name"]] = "Не найдено"
                    except Exception as e:
                        page_data[element["name"]] = f"Ошибка: {str(e)}"

                self.results.append(page_data)
                self.logger.info(f"Успешно обработана: {url}")
                pages_since_restart += 1
                self.save_temp_results()

                time.sleep(random.uniform(1, 2))

                def update_success():
                    if self.parsing_in_progress:
                        self.update_progress(i + 1, total_links, short_url)
                        self._display_results()
                self.root.after(0, update_success)

            except Exception as e:
                print(f"  ✗ Ошибка при обработке {url}: {e}")
                self.logger.error(f"Ошибка при обработке {url}: {str(e)}")
                error_data = {"url": url, "error": str(e)}
                for element in self.selected_elements:
                    error_data[element["name"]] = "Ошибка загрузки"
                self.results.append(error_data)
                self.save_temp_results()
                pages_since_restart += 1

                def update_error():
                    if self.parsing_in_progress:
                        self.update_progress(i + 1, total_links, f"ERROR: {short_url}")
                        self._display_results()
                self.root.after(0, update_error)

        def final_update():
            self.parsing_in_progress = False
            if len(self.results) == total_links:
                self.status_var.set(f"Парсинг завершен. Обработано: {len(self.results)} страниц")
            else:
                self.status_var.set(f"Парсинг остановлен. Обработано: {len(self.results)} страниц")
            self._display_results()
            self.start_parsing_btn.config(state=tk.NORMAL)
            self.stop_parsing_btn.config(state=tk.DISABLED)
        self.root.after(0, final_update)

    def _display_results(self):
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        if not self.results:
            return
        columns = list(self.results[0].keys())
        self.results_tree["columns"] = columns
        self.results_tree["show"] = "headings"
        for col in columns:
            self.results_tree.heading(col, text=col, anchor='w')
            self.results_tree.column(col, width=200, anchor='w', minwidth=100)
        for result in self.results:
            values = [result.get(col, "") for col in columns]
            self.results_tree.insert("", tk.END, values=values)

    def export_excel(self):
        if not self.results:
            messagebox.showwarning("Предупреждение", "Нет данных для экспорта")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
        if file_path:
            try:
                df = pd.DataFrame(self.results)
                df.to_excel(file_path, index=False)
                messagebox.showinfo("Успех", f"Данные экспортированы в {file_path}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось экспортировать данные: {str(e)}")

    def export_json(self):
        if not self.results:
            messagebox.showwarning("Предупреждение", "Нет данных для экспорта")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as file:
                    json.dump(self.results, file, ensure_ascii=False, indent=2)
                messagebox.showinfo("Успех", f"Данные экспортированы в {file_path}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось экспортировать данные: {str(e)}")

    def clear_results(self):
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        self.results.clear()
        if os.path.exists(self.temp_results_file):
            os.remove(self.temp_results_file)

    def __del__(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass


def main():
    root = tk.Tk()
    # Настройка глобальных стилей кнопок
    style = ttk.Style()
    style.theme_use('clam')
    style.configure("Accent.TButton", foreground="white", background="#3498db", font=('Arial', 10, 'bold'))
    style.map("Accent.TButton", background=[('active', '#2980b9')])
    style.configure("Stop.TButton", foreground="white", background="#e74c3c", font=('Arial', 10, 'bold'))
    style.map("Stop.TButton", background=[('active', '#c0392b')])
    style.configure("Click.TButton", foreground="white", background="#2ecc71", font=('Arial', 10, 'bold'))
    style.map("Click.TButton", background=[('active', '#27ae60')])

    app = UniversalParser(root)
    root.mainloop()


if __name__ == "__main__":
    main()