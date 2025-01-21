import os
import re
import requests
from pathlib import Path
from tqdm import tqdm
import hashlib
import datetime
import hmac
import xml.etree.ElementTree as ET


ENDPOINT_URL = os.environ.get("R2_API")
AWS_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY")
AWS_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET")
REGION = "auto"

# カスタムドメイン
CUSTOM_DOMAIN = f"https://storage.sotono.dev"

# Markdownが入っているディレクトリ
# 絶対パスで指定する
md_directory = "../_text/Obsidian_Mitumine/contents/"

# Cloudflare R2のバケット
# "bucket_name/img_folder"の形になる
bucket_name = "bucket-1"
img_folder = "img/"


if not ENDPOINT_URL or not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
    print("Error: 必要な環境変数が設定されていません。")
    exit(1)


def upload_to_r2(image_path, bucket_name, object_name):
    date = datetime.datetime.now(datetime.timezone.utc)

    host = ENDPOINT_URL.split("//")[-1].split("/")[0]
    credential = (
        f"{AWS_ACCESS_KEY_ID}/{date.strftime('%Y%m%d')}/{REGION}/s3/aws4_request"
    )
    signed_headers = "host;x-amz-content-sha256;x-amz-date"

    # 署名の計算
    with open(image_path, "rb") as image_file:
        image_data = image_file.read()
        signature, time_stamp = get_signature(
            date,
            REGION,
            bucket_name,
            object_name,
            method="PUT",
            payload=image_data,
        )

    # HTTP PUT リクエストを送信
    headers = {
        "Host": host,
        "Content-Type": "image/jpeg",
        "x-amz-date": time_stamp,
        "x-amz-content-sha256": hashlib.sha256(image_data).hexdigest(),
        "Authorization": f"AWS4-HMAC-SHA256 Credential={credential}, SignedHeaders={signed_headers}, Signature={signature}",
    }

    url = f"{ENDPOINT_URL}/{bucket_name}/{object_name}"

    response = requests.put(
        url,
        headers=headers,
        data=image_data,
    )

    if response.status_code == 200:
        public_url = f"{CUSTOM_DOMAIN}/{object_name}"
        return public_url
    else:
        print(f"Error uploading to R2: {response.text}")
        return None


def get_signature(
    date, region, bucket_name, object_name=None, method="GET", payload=b""
):
    """AWS Signature Version 4の署名を生成"""
    algorithm = "AWS4-HMAC-SHA256"
    service = "s3"
    request_type = "aws4_request"

    # 現在のUTC時間と日付
    request_date_time = date.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = date.strftime("%Y%m%d")

    # Canonical Request の作成
    canonical_uri = f"/{bucket_name}"
    if object_name:
        canonical_uri += f"/{object_name}"

    canonical_querystring = ""
    host = ENDPOINT_URL.split("//")[-1].split("/")[0]

    # ペイロードのハッシュを計算
    payload_hash = hashlib.sha256(payload).hexdigest()

    canonical_headers = (
        f"host:{host}\n"
        f"x-amz-content-sha256:{payload_hash}\n"
        f"x-amz-date:{request_date_time}\n"
    )
    signed_headers = "host;x-amz-content-sha256;x-amz-date"

    canonical_request = (
        f"{method}\n"
        f"{canonical_uri}\n"
        f"{canonical_querystring}\n"
        f"{canonical_headers}\n"
        f"{signed_headers}\n"
        f"{payload_hash}"
    )

    # String to Sign の作成
    credential_scope = f"{date_stamp}/{region}/{service}/{request_type}"
    string_to_sign = (
        f"{algorithm}\n"
        f"{request_date_time}\n"
        f"{credential_scope}\n"
        f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
    )

    k_date = sign(("AWS4" + AWS_SECRET_ACCESS_KEY).encode("utf-8"), date_stamp)
    k_region = sign(k_date, region)
    k_service = sign(k_region, service)
    signing_key = sign(k_service, request_type)

    # 最終署名の計算
    signature = hmac.new(
        signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    return signature, request_date_time


def sign(key, msg):
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def download_image_from_imgur(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # HTTPエラーを発生させる
        return response.content
    except requests.exceptions.RequestException as e:
        print(f"Error downloading image from {url}: {e}")
        return None


def main():
    markdown_files = list(Path(md_directory).rglob("*.md"))

    for md_file in tqdm(markdown_files, desc="Processing Markdown files"):
        with open(md_file, "r", encoding="utf-8") as file:
            content = file.read()

        imgur_urls = re.findall(
            r"(https?://i\.imgur\.com/[A-Za-z0-9]+\.(?:png|jpg|jpeg|gif))", content
        )

        for imgur_url in tqdm(imgur_urls, desc="Downloading Imgur images", leave=False):
            image_data = download_image_from_imgur(imgur_url)
            if image_data:
                image_path = f"{md_file.parent}/{os.path.basename(imgur_url)}"

                with open(image_path, "wb") as image_file:
                    image_file.write(image_data)
                r2_url = upload_to_r2(
                    image_path,
                    bucket_name,
                    f"{img_folder}{os.path.basename(imgur_url)}",
                )
                content = content.replace(imgur_url, r2_url)
                os.remove(image_path)

        # 更新された内容をMarkdownファイルに書き込む
        with open(md_file, "w", encoding="utf-8") as file:
            file.write(content)


if __name__ == "__main__":
    main()
