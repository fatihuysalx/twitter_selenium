import requests
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
import os
import time
from datetime import datetime

# AYARLAR
SAVE_PATH = r"D:\OneDrive\Desktop\SeleniumData"
os.makedirs(SAVE_PATH, exist_ok=True)

# 1. Trend başlıklarını otomatik çekiyoruz (TwitterAPI.io)
def get_trends_from_api():
    url = "https://api.twitterapi.io/twitter/trends?woeid=23424969"
    headers = {"x-api-key": "...."}
    response = requests.get(url, headers=headers)
    trends_data = response.json()
    hashtags = []
    for t in trends_data["trends"]:
        query = t["trend"]["target"]["query"]
        hashtags.append(query.replace("#", "").replace("\"", ""))
    return hashtags

# 2. Tweetleri Selenium ile indir + görselleri kaydet
def download_tweets_and_images(hashtags, TWITTER_USER, TWITTER_PASS):
    all_tweets = []
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.get("https://twitter.com/login")
    time.sleep(3)

    # Login
    username_input = driver.find_element(By.NAME, "text")
    username_input.send_keys(TWITTER_USER)
    username_input.send_keys(Keys.ENTER)
    time.sleep(2)
    password_input = driver.find_element(By.NAME, "password")
    password_input.send_keys(TWITTER_PASS)
    password_input.send_keys(Keys.ENTER)
    time.sleep(5)

    # Her hashtag için tweet çekimi
    for hashtag in hashtags:
        print(f"--- #{hashtag} için tweetler çekiliyor ---")
        driver.get(f"https://twitter.com/search?q=%23{hashtag}&src=typed_query&f=live")
        time.sleep(5)
        tweets = driver.find_elements(By.XPATH, '//article[@data-testid="tweet"]')[:1]  # Sadece 1 tweet
        for idx, t in enumerate(tweets, 1):
            tweet_data = {"hashtag": hashtag}
            try:
                tweet_data['tweet_text'] = t.find_element(By.XPATH, './/div[@data-testid="tweetText"]').text
            except:
                tweet_data['tweet_text'] = ""
            try:
                tweet_data['username'] = t.find_element(By.XPATH, './/div[@data-testid="User-Names"]//span').text
            except:
                tweet_data['username'] = ""
            try:
                tweet_data['tweet_time'] = t.find_element(By.XPATH, ".//time").get_attribute("datetime")
            except:
                tweet_data['tweet_time'] = ""
            try:
                hashtags_in_tweet = [e.text for e in t.find_elements(By.XPATH, ".//a[contains(@href, '/hashtag/')]")]
                tweet_data['hashtags_in_tweet'] = hashtags_in_tweet
            except:
                tweet_data['hashtags_in_tweet'] = []

            img_paths = []
            imgs = t.find_elements(By.XPATH, './/img[contains(@src,"twimg")]')
            for img_num in range(len(imgs)):
                for attempt in range(3):  # 3 kez dene
                    try:
                        img = t.find_elements(By.XPATH, './/img[contains(@src,"twimg")]')[img_num]
                        img_url = img.get_attribute("src")
                        if "profile_images" not in img_url:
                            ext = os.path.splitext(img_url)[1].split("?")[0] or ".jpg"
                            timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
                            filename = f"{hashtag}_{idx}_{img_num+1}_{timestamp}{ext}"
                            filepath = os.path.join(SAVE_PATH, filename)
                            try:
                                r = requests.get(img_url, timeout=10)
                                if r.ok:
                                    with open(filepath, "wb") as fimg:
                                        fimg.write(r.content)
                                    img_paths.append(filename)
                            except Exception as e:
                                print(f"Görsel indirilemedi: {img_url} Hata: {e}")
                        break  # başarılıysa çık
                    except Exception as e:
                        print(f"Tekrar denenecek, hata: {e}")
                        time.sleep(0.5)
                        continue
            tweet_data['img_files'] = img_paths

            # --- EN ÖNEMLİ KISIM: BOŞ METİNLERİ EKLEME! ---
            if tweet_data['tweet_text'].strip() != "":
                all_tweets.append(tweet_data)
            # boşsa ekleme, direkt atla

    driver.quit()
    return all_tweets

# 3. JSON’a kaydet
def save_tweets_to_json(tweet_data_list):
    json_path = os.path.join(SAVE_PATH, "tweetler.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(tweet_data_list, f, ensure_ascii=False, indent=2)
    print(f"Tüm tweetler ve görseller {SAVE_PATH} yoluna kaydedildi!")

# 4. Ana çalışma akışı
if __name__ == "__main__":
    load_dotenv()
    TWITTER_USER = os.getenv("TWITTER_USER")
    TWITTER_PASS = os.getenv("TWITTER_PASS")
    hashtags = get_trends_from_api()
    print("Trendler:", hashtags)
    tweet_data_list = download_tweets_and_images(hashtags, TWITTER_USER, TWITTER_PASS)
    print(f"{len(tweet_data_list)} tweet toplandı.")
    save_tweets_to_json(tweet_data_list)
