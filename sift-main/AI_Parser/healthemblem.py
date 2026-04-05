import os
from playwright.sync_api import sync_playwright

# --- CONFIG ---
BASE_URL = "https://gatewaypa.com/emblemhealth/policydisplay/55"
DOWNLOAD_PREFIX = "https://gatewaypa.com/"

def download_drug_policy(drug_name):
    """
    Inputs a drug name, intercepts the gateway data, 
    and downloads the matching PDF.
    """
    with sync_playwright() as p:
        # Launching browser
        # Set headless=False if you want to see the window pop up
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print(f"Accessing Gateway for: {drug_name}...")
        
        intercepted_data = []

        # Internal listener to catch the JSON directory
        def handle_response(response):
            if "/api/policydisplay/" in response.url and response.status == 200:
                try:
                    intercepted_data.append(response.json())
                except:
                    pass

        page.on("response", handle_response)
        
        try:
            # Navigate and wait for the table to populate
            page.goto(BASE_URL, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(3000) 

            if not intercepted_data:
                print("Error: No API data intercepted.")
                browser.close()
                return None

            os.makedirs("downloads", exist_ok=True)

            # Search logic
            for data in intercepted_data:
                sections = data.get("linkSections", []) if isinstance(data, dict) else []
                for section in sections:
                    for link in section.get("links", []):
                        # Matching against linkText and SubText
                        text = f"{link.get('linkText','')} {link.get('linkSubText','')}".lower()
                        
                        if drug_name.lower() in text:
                            url_path = link.get("linkUrl", "").lstrip('/')
                            final_url = f"{DOWNLOAD_PREFIX}{url_path}"
                            
                            print(f"Downloading: {link.get('linkText')}")
                            
                            # Perform download using the browser's authenticated context
                            pdf_download = page.request.get(final_url)
                            if pdf_download.status == 200:
                                filename = f"downloads/{drug_name.replace(' ', '_')}.pdf"
                                with open(filename, "wb") as f:
                                    f.write(pdf_download.body())
                                print(f"Success: Saved to {filename}")
                                browser.close()
                                return filename
            
            print(f"Could not find a policy matching '{drug_name}'")
            
        except Exception as e:
            print(f"Execution Error: {e}")
        
        browser.close()
        return None

# --- EXAMPLE USAGE ---
if __name__ == "__main__":
    # You can now call it with any name
    target = "Bavencio"
    result = download_drug_policy(target)
    
    if result:
        print(f"Finished processing {target}.")