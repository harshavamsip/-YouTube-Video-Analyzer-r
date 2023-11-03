import os
from flask import Flask, render_template, request, redirect, url_for
import googleapiclient.discovery
from textblob import TextBlob
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import ssl

# Disable SSL certificate verification for this example (not recommended for production use)
ssl._create_default_https_context = ssl._create_unverified_context

app = Flask(__name__)

# Set your YouTube Data API key here
YOUTUBE_API_KEY = "AIzaSyCvtRnKGLMgtNexVGm0jN_weLQ3xogV4hM"

# Initialize the YouTube Data API client
youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

# Initialize video ID storage
video_ids = []

# Function to search for videos and retrieve video details
def search_and_recommend_videos(query, max_results=10):
    response = youtube.search().list(
        q=query,
        type="video",
        part="id,snippet",
        maxResults=max_results,
        videoCaption="any",
    ).execute()

    video_details = []
    for item in response.get("items", []):
        video_id = item["id"]["videoId"]
        title = item["snippet"]["title"]
        description = item["snippet"]["description"]
        published_at = item["snippet"]["publishedAt"]

        link = f"https://www.youtube.com/watch?v={video_id}"

        # Use a separate request to get video statistics
        video_statistics = youtube.videos().list(
            part="statistics",
            id=video_id
        ).execute()

        likes = 0
        views = 0

        if "items" in video_statistics:
            statistics = video_statistics["items"][0]["statistics"]
            likes = int(statistics.get("likeCount", 0))
            views = int(statistics.get("viewCount", 0))

        video_details.append((title, link, video_id, description, published_at, likes, views))

    return video_details

# Function to store video IDs
def store_video_id(video_id):
    video_ids.append(video_id)

# Function to fetch video comments
def get_video_comments(video_id):
    comments = []
    results = youtube.commentThreads().list(
        part="snippet",
        videoId=video_id,
        textFormat="plainText",
        maxResults=100
    ).execute()

    while "items" in results:
        for item in results["items"]:
            comment = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
            comments.append(comment)
        if "nextPageToken" in results:
            results = youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                textFormat="plainText",
                maxResults=100,
                pageToken=results["nextPageToken"]
            ).execute()
        else:
            break

    return comments

# Function to perform sentiment analysis and categorize comments
def analyze_and_categorize_comments(comments):
    categorized_comments = {
        "Positive": [],
        "Negative": [],
        "Neutral": []
    }

    for comment in comments:
        analysis = TextBlob(comment)
        sentiment_polarity = analysis.sentiment.polarity

        # Categorize based on polarity
        if sentiment_polarity > 0.2:
            categorized_comments["Positive"].append(comment)
        elif sentiment_polarity < -0.2:
            categorized_comments["Negative"].append(comment)
        else:
            categorized_comments["Neutral"].append(comment)

    return categorized_comments

# Function to generate a word cloud from comments
def generate_word_cloud(comments):
    all_comments = ' '.join(comments)
    wordcloud = WordCloud(width=800, height=400, background_color='white').generate(all_comments)
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    word_cloud_image = plt_to_base64(plt)
    return word_cloud_image

# Function to convert Matplotlib plot to base64 image
def plt_to_base64(plt):
    import base64
    from io import BytesIO

    img_buf = BytesIO()
    plt.savefig(img_buf, format="png", bbox_inches="tight")
    img_buf.seek(0)
    img_data = base64.b64encode(img_buf.read()).decode("utf-8")
    return img_data

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        search_query = request.form['search_query']
        video_details = search_and_recommend_videos(search_query)
        return render_template('index.html', video_details=video_details)

    return render_template('index.html', video_details=None)

@app.route('/video_selection', methods=['GET', 'POST'])
def video_selection():
    if request.method == 'POST':
        video_id = request.form['video_id']
        store_video_id(video_id)
        return redirect(url_for('video_analysis', video_id=video_id))

    video_details = search_and_recommend_videos("Your default query goes here")  # Provide a default query
    return render_template('video_selection.html', video_details=video_details)

@app.route('/video_analysis', methods=['GET', 'POST'])
def video_analysis():
    if request.method == 'GET':
        video_id = request.args.get('video_id')
        comments = get_video_comments(video_id)
        categorized_comments = analyze_and_categorize_comments(comments)
        word_cloud_image = generate_word_cloud(comments)

        return render_template('video_analysis.html', video_id=video_id, categorized_comments=categorized_comments, word_cloud=word_cloud_image)

    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
