import os
import time
import re
import logging
from flask import Flask, request, jsonify
from seleniumbase import Driver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_server_automation(username, email, password):
    driver = None
    try:
        # تهيئة المتصفح في وضع UC (غير قابل للكشف) وبدون واجهة
        driver = Driver(uc=True, headless2=True, no_sandbox=True)
        driver.implicitly_wait(10)
        wait = WebDriverWait(driver, 60)

        logger.info("فتح صفحة التسجيل...")
        driver.get("https://wispbyte.com/register")
        time.sleep(3)

        # انتظار لحل تحدي Cloudflare Turnstile (انتظار بسيط، قد تحتاج إلى تعديل)
        logger.info("انتظار تجاوز تحدي Turnstile...")
        time.sleep(12)

        # ملء النموذج
        driver.find_element(By.NAME, "username").send_keys(username)
        driver.find_element(By.NAME, "email").send_keys(email)
        driver.find_element(By.NAME, "password").send_keys(password)
        driver.find_element(By.NAME, "confirm_password").send_keys(password)

        # الضغط على زر التسجيل
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        time.sleep(5)

        # التحقق من الحاجة لتفعيل البريد
        current_url = driver.current_url
        if "verify" in current_url or "confirmation" in current_url:
            return {"status": "warning", "message": "تم إنشاء الحساب ولكن يجب تفعيل البريد الإلكتروني."}

        # الانتقال إلى لوحة التحكم
        driver.get("https://wispbyte.com/dashboard")
        time.sleep(3)

        # إنشاء سيرفر جديد
        try:
            driver.find_element(By.LINK_TEXT, "Create Server").click()
        except:
            return {"status": "error", "message": "لم يتم العثور على زر إنشاء السيرفر."}
        time.sleep(2)

        driver.find_element(By.NAME, "server_name").send_keys(f"{username}_server")
        # اختيار الخطة المجانية
        try:
            driver.find_element(By.XPATH, "//input[@value='free']").click()
        except:
            pass
        # اختيار بيئة Python (إذا وجدت)
        try:
            driver.find_element(By.XPATH, "//option[contains(text(), 'Python')]").click()
        except:
            pass
        # الضغط على زر الإنشاء
        driver.find_element(By.XPATH, "//button[contains(text(), 'Create')]").click()
        time.sleep(10)

        # استخراج عنوان IP
        ip_elem = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'IP:')]")))
        ip_text = ip_elem.text
        ip_match = re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', ip_text)
        if ip_match:
            return {"status": "success", "ip": ip_match.group(0)}
        else:
            return {"status": "error", "message": "تعذر استخراج عنوان IP."}

    except Exception as e:
        logger.exception("خطأ في الأتمتة")
        return {"status": "error", "message": str(e)}
    finally:
        if driver:
            driver.quit()

@app.route('/')
def index():
    return jsonify({"message": "Wispbyte API is running"})

@app.route('/create_server', methods=['POST'])
def create_server():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    if not username or not email or not password:
        return jsonify({"status": "error", "message": "جميع الحقول مطلوبة"})
    result = create_server_automation(username, email, password)
    return jsonify(result)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)