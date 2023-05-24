from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as wait
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService 
import undetected_chromedriver as uc
import pandas as pd
import time
import csv
import sys
import numpy as np
import re 

def initialize_bot():

    # Setting up chrome driver for the bot
    chrome_options  = webdriver.ChromeOptions()
    # suppressing output messages from the driver
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--window-size=1920,1080')
    # adding user agents
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36")
    chrome_options.add_argument("--incognito")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    # running the driver with no browser window
    #chrome_options.add_argument('--headless')
    # disabling images rendering 
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.page_load_strategy = 'normal'
    # installing the chrome driver
    driver_path = ChromeDriverManager().install()
    chrome_service = ChromeService(driver_path)
    # configuring the driver
    driver = webdriver.Chrome(options=chrome_options, service=chrome_service)
    driver.set_page_load_timeout(10000)
    driver.maximize_window()

    return driver

def scrape_fictiondb(path):

    start = time.time()
    print('-'*75)
    print('Scraping fictiondb.com ...')
    print('-'*75)
    # initialize the web driver
    driver = initialize_bot()

    # initializing the dataframe
    data = pd.DataFrame()

    # if no books links provided then get the links
    if path == '':
        name = 'fictiondb_data.xlsx'
        # getting the books under each category
        links, pages = [], []   
        homepage = "https://www.fictiondb.com/awards/awards.htm"

        nbooks, nawards = 0, 0
        driver.get(homepage)
        div = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.row")))
        tags = wait(div, 2).until(EC.presence_of_all_elements_located((By.TAG_NAME, "h5")))
        for tag in tags:
            url = wait(tag, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "a.dkblue"))).get_attribute('href')
            nawards += 1
            print(f'Getting award link {nawards}')
            pages.append(url)

        for page in pages:
            driver.get(page)
            # scraping books urls
            titles = wait(driver, 2).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.col-md-3.col-xl-2")))

            for title in titles:
                try:                                  
                    link = wait(title, 2).until(EC.presence_of_element_located((By.TAG_NAME, "a"))).get_attribute('href')
                    links.append(link)
                    nbooks += 1 
                    print(f'Scraping the url for book {nbooks}')
                except Exception as err:
                    pass
                    
        # saving the links to a csv file
        print('-'*75)
        print('Exporting links to a csv file ....')
        with open('fictiondb_links.csv', 'w', newline='\n', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Link'])
            for row in links:
                writer.writerow([row])

    scraped = []
    if path != '':
        df_links = pd.read_csv(path)
        name = path.split('\\')[-1][:-4]
        name = name + '_data.xlsx'
    else:
        df_links = pd.read_csv('fictiondb_links.csv')

    links = df_links['Link'].values.tolist()

    try:
        data = pd.read_excel(name)
        scraped = data['Title Link'].values.tolist()
    except:
        pass

    # scraping books details
    print('-'*75)
    print('Scraping Books Info...')
    print('-'*75)
    n = len(links)
    for i, link in enumerate(links):
        try:
            if link in scraped: continue
            driver.get(link)           
            details = {}
            print(f'Scraping the info for book {i+1}\{n}')            
            # title and title link
            title_link, title = '', ''              
            try:
                title_link = link
                title = wait(driver, 2).until(EC.presence_of_element_located((By.TAG_NAME, "h1"))).get_attribute('textContent').replace('\n', '').split('—')[0].strip().title() 
            except:
                print(f'Warning: failed to scrape the title for book: {link}')               
                
            details['Title'] = title
            details['Title Link'] = title_link                          
            # Author and author link
            author, author_link = '', ''
            try:
                h1 = wait(driver, 2).until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
                tags = wait(h1, 2).until(EC.presence_of_all_elements_located((By.TAG_NAME, "a")))
                for tag in tags:
                    author_link += tag.get_attribute('href') + ', '
                    author += tag.get_attribute('textContent') + ', '

                details['Author'] = author[:-2]            
                details['Author Link'] = author_link[:-2]
            except:
                pass
                               
            # other info
            form, genre, period, date, npages, age, Amazon, rating = '', '', '', '', '', '', '', ''
            try:
                ul = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul.project-details-list")))       
                lis = wait(ul, 2).until(EC.presence_of_all_elements_located((By.TAG_NAME, "li")))       
                for li in lis:
                    text = li.get_attribute('textContent')
                    if 'Published:' in text:
                        date = text.replace('Published:', '').strip()
                    elif 'Formats:' in text:
                        form = text.replace('Formats:', '').replace('\n', '').replace(' / ', ', ').strip()
                    elif 'Main Genre:' in text:
                        genre = text.replace('Main Genre:', '').replace('\n', '').strip()
                    elif 'Time Period:' in text:
                        period = text.replace('Time Period:', '').replace('\n', '').strip()
                    elif 'Pages:' in text:
                        npages = text.replace('Pages:', '').replace('\n', '').strip()  
                    elif 'Age Level:' in text:
                        age = text.replace('Age Level:', '').replace('\n', '').strip()              
                    elif 'Rating:' in text:
                        stars = wait(li, 2).until(EC.presence_of_all_elements_located((By.TAG_NAME, "use")))
                        rating = 0
                        for star in stars:
                            label = star.get_attribute('xlink:href').split('#')[-1]
                            if 'fill' in label:
                                rating += 1
                            elif 'half' in label:
                                rating += 0.5
                    elif 'Purchase:' in text:
                        Amazon = wait(li, 2).until(EC.presence_of_element_located((By.TAG_NAME, "a"))).get_attribute('href')                     
            except:
                pass          
                
            details['Publication Date'] = date 
            details['Formats'] = form 
            details['Genre'] = genre 
            details['Time Period'] = period 
            details['Page Count'] = npages 
            details['Age'] = age 
            details['Rating'] = rating 
            details['Amazon Link'] = Amazon 
                           
            # publication info
            publisher, ISBN, ISBN13 = '', '', ''
            try:
                div = wait(driver, 2).until(EC.presence_of_element_located((By.XPATH, "//div[@class='tab-pane active']")))
                li = wait(div, 2).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li[class='col-lg-4 col-xl-3']")))[-1]
                lis = wait(li, 2).until(EC.presence_of_all_elements_located((By.TAG_NAME, "li")))
                for li in lis:
                    text = li.get_attribute('textContent')
                    if 'ISBN13:' in text:
                        ISBN13 = text.replace('ISBN13:', '').replace('\n', '').strip()
                    elif 'ISBN:' in text:
                        ISBN = text.replace('ISBN:', '').replace('\n', '').strip()
                if len(lis) > 2:
                    publisher = lis[2].get_attribute('textContent').strip()
            except:
                pass  
            
            details['ISBN'] = ISBN 
            details['ISBN-13'] = ISBN13 
            details['Publisher'] = publisher 
       
            try:
                driver.get(details['Amazon Link'])
                div = wait(driver, 2).until(EC.presence_of_element_located((By.XPATH, "//div[@class='owl-wrapper']")))
                Amazon = wait(div, 2).until(EC.presence_of_element_located((By.TAG_NAME, "a"))).get_attribute('href')
                if 'www.amazon' not in Amazon:
                    Amazon = ''
                details['Amazon Link'] = Amazon
            except:
                details['Amazon Link'] = ''

            # appending the output to the datafame       
            data = data.append([details.copy()])
            # saving data to csv file each 100 links
            if np.mod(i+1, 100) == 0:
                print('Outputting scraped data ...')
                data.to_excel(name, index=False)
        except Exception as err:
            print(str(err))
            driver.quit()
            driver = initialize_bot()

    # optional output to excel
    data.to_excel(name, index=False)
    elapsed = round((time.time() - start)/60, 2)
    print('-'*75)
    print(f'fictiondb.com scraping process completed successfully! Elapsed time {elapsed} mins')
    print('-'*75)
    driver.quit()

    return data

if __name__ == "__main__":
    
    path = ''
    if len(sys.argv) == 2:
        path = sys.argv[1]
    data = scrape_fictiondb(path)

