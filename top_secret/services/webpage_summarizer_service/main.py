from multiprocessing import Process, Queue, set_start_method

import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from fastapi import FastAPI
from pydantic import BaseModel
from bs4 import BeautifulSoup
from newspaper import Article
import nltk


nltk.download("punkt")  # Required for NLP tasks in newspaper3k


class PageScraper:
    def __init__(self, url):
        self.url = url

    def get_request(self):
        return scrapy.Request(
            url=self.url,
            meta={
                "playwright": True,
                "playwright_include_page": True,
                "playwright_page_methods": [
                    # Add any PageMethods you need here, e.g., to wait for a selector
                ],
            },
        )


class ResultParser:
    def __init__(self, method="css", expression=None):
        self.method = method
        self.expression = expression

    def clean_html(self, html_content):
        soup = BeautifulSoup(html_content, "html.parser")

        # Remove script and style elements
        for script_or_style in soup(["script", "style"]):
            script_or_style.extract()

        # Remove hidden elements and images
        for hidden in soup.find_all(
            style=lambda value: "display:none" in (value or "").lower()
        ):
            hidden.extract()
        for img in soup.find_all("img"):
            img.extract()

        # You can add more rules here to remove other unwanted tags

        # Return the cleaned HTML as a string
        return str(soup)

    def parse(self, content):
        # Clean the HTML content first
        cleaned_html = self.clean_html(content.body)

        # Create a new Selector object from the cleaned HTML
        cleaned_selector = scrapy.Selector(text=cleaned_html)

        # Use the cleaned selector for parsing
        if self.method == "css":
            return cleaned_selector.css(self.expression).getall()
        elif self.method == "xpath":
            return cleaned_selector.xpath(self.expression).getall()
        else:
            raise ValueError("Invalid parsing method specified. Use 'css' or 'xpath'.")


class ScrapySpider(scrapy.Spider):
    name = "scrapy_spider"

    def __init__(self, scraper, parser, results_queue, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scraper = scraper
        self.parser = parser
        self.results_queue = results_queue
        self.crawled_data = []  # Initialize an empty list to store results

    def start_requests(self):
        yield self.scraper.get_request()

    def closed(self, reason):
        # Put the results into the queue
        self.results_queue.put(self.crawled_data)

    def parse(self, response, **kwargs):
        parsed_results = self.parser.parse(response)

        # Join the list of strings into a single string if parsed_results is a list
        if isinstance(parsed_results, list):
            parsed_results = " ".join(parsed_results)

        # Ensure parsed_results is a string
        if not isinstance(parsed_results, str):
            raise ValueError("parsed_results is not a string.")

        # Proceed with article parsing
        article = Article("")
        article.set_html(parsed_results)
        article.parse()
        article.nlp()  # Perform NLP tasks like summarization
        full_text = article.text

        # # Create an item with the extracted data
        # print("summarizing...")
        # print("full_text: ", full_text)
        # post_data = {
        #     "prompt": "Summarize This:" + str(full_text),
        #     "model": "gpt-3.5-turbo",
        #     "custom_url": "Optional custom URL here",
        # }

        yield {"result": full_text}
        # scrapy.Request(
        #     "http://localhost:8001/completion",
        #     method="POST",
        #     body=json.dumps(post_data),
        #     headers={"Content-Type": "application/json"},
        #     callback=self.parse_summary,
        #     meta={"full_text": full_text},
        # )

    # def parse_summary(self, response):
    #     full_text = response.meta["full_text"]
    #     summary = "Error: Unable to get summary"
    #     try:
    #         # Use response.json() to parse the JSON response directly
    #         data = response.json()
    #         summary = data.get("completion", "")
    #     except ValueError as e:
    #         # Handle the case where the response is not valid JSON
    #         self.logger.error(f"Failed to parse JSON: {e}")

    #     item = {
    #         "full_text": full_text,
    #         "summary": summary,
    #     }

    #     self.crawled_data.append(item)  # Append the scraped data to crawled_data
    #     yield item  # Yield the item to be processed by Scrapy's item pipeline


app = FastAPI()


class ScrapeRequest(BaseModel):
    url: str
    parse_method: str
    parse_expression: str


def run_crawler(scraper, parser, results_queue):
    custom_settings = {
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",  # or 'firefox' or 'webkit'
        "PLAYWRIGHT_LAUNCH_OPTIONS": {
            "headless": True,
            "timeout": 20 * 1000,  # 20 seconds
        },
        # Optionally, set the USER_AGENT to None if you want to use the
        # browser's default
        # 'USER_AGENT': None,
    }

    settings = get_project_settings()
    settings.update(custom_settings)
    process = CrawlerProcess(settings=settings)
    process.crawl(
        ScrapySpider, scraper=scraper, parser=parser, results_queue=results_queue
    )
    process.start()
    process.join()


@app.post("/scrape-url")
async def scrape_url(request: ScrapeRequest):
    # Set the start method for multiprocessing to 'spawn'
    set_start_method("spawn", force=True)

    scraper = PageScraper(url=request.url)
    parser = ResultParser(
        method=request.parse_method, expression=request.parse_expression
    )

    # Create a queue for the results
    results_queue = Queue()

    # Start the crawler in a separate process
    process = Process(target=run_crawler, args=(scraper, parser, results_queue))
    process.start()
    process.join()  # Wait for the process to complete

    # Retrieve results from the queue
    results = results_queue.get() if not results_queue.empty() else None

    return {"message": "Scraping completed", "data": results}
