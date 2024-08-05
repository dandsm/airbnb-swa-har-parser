import csv
import io
import json

import azure.functions as func
import logging

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="airbnb-har-parser")
def airbnb_har_parser(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:

        input_file = req.files.get('file')
        if not input_file:
            return func.HttpResponse("No file uploaded", status_code=400)
        
        har_data = json.load(input_file)
        listings = parse_har_to_array(har_data)
        output_file = parse_array_csv_memory(listings)

        res = func.HttpResponse(output_file.getvalue(), mimetype='text/csv')
        res.headers['Content-Disposition'] = 'attachment; filename=airbnb_data.csv'
        
        return res
    
    except Exception as e:
        logging.error(f"Error processing request: {e}")
        return func.HttpResponse(str(e), status_code=500)

def parse_har_to_array(har_data):
    listings = []

    for entry in har_data['log']['entries']:
        request = entry['request']
        response = entry['response']

        if 'https://www.airbnb.com/api/v3/StaysSearch' in request['url']:
            res_content_json = json.loads(response['content']['text'])
            for search_result in res_content_json["data"]["presentation"]["staysSearch"]["mapResults"]["mapSearchResults"]:
                if search_result["__typename"] == "StaySearchResult":
                    listings.append({
                        "id": search_result["listing"]["id"],
                        "name": search_result["listing"]["name"].replace(",", " "),
                        "title": search_result["listing"]["title"].replace(",", " "),
                        "badges": " & ".join([badge["text"] for badge in search_result["listing"]["formattedBadges"]]),
                        "avg_rating": float(search_result["listing"]["avgRatingLocalized"].split(' ')[0]) if search_result["listing"]["avgRatingLocalized"] is not None and search_result["listing"]["avgRatingLocalized"] != "New" else -1,
                        "reviews_count": int(search_result["listing"]["avgRatingLocalized"].split(' ')[1].strip("()")) if search_result["listing"]["avgRatingLocalized"] is not None and search_result["listing"]["avgRatingLocalized"] != "New" else 0,
                        "room_category": search_result["listing"]["roomTypeCategory"],
                        "beds_count": int(search_result["listing"]["structuredContent"]["primaryLine"][0]["body"].split(' ')[0]) if "primaryLine" in search_result["listing"]["structuredContent"] and search_result["listing"]["structuredContent"]["primaryLine"] is not None and len(search_result["listing"]["structuredContent"]["primaryLine"]) > 0  else -1,
                        "beds": search_result["listing"]["structuredContent"]["primaryLine"][0]["body"] if "primaryLine" in search_result["listing"]["structuredContent"] and search_result["listing"]["structuredContent"]["primaryLine"] is not None and len(search_result["listing"]["structuredContent"]["primaryLine"]) > 0  else "",
                        "price":  search_result["pricingQuote"]["structuredStayDisplayPrice"]["primaryLine"]["price"] if "price" in search_result["pricingQuote"]["structuredStayDisplayPrice"]["primaryLine"] else search_result["pricingQuote"]["structuredStayDisplayPrice"]["primaryLine"]["originalPrice"],
                        "price_label":  search_result["pricingQuote"]["structuredStayDisplayPrice"]["primaryLine"]["accessibilityLabel"].replace(",", " "),
                    })
    
    return listings


def parse_array_csv_memory(listings):
    # Create an in-memory file
    output = io.StringIO()
    # Create a CSV writer object
    writer = csv.writer(output)

    # Write the header
    file_headers = listings[0].keys()
    writer.writerow(file_headers)

    # Write each dictionary as a row in the CSV
    for entry in listings:
        row = [str(entry[key]) for key in file_headers]  # Convert each value to a string
        writer.writerow(row)
    
    output.seek(0)

    return output
