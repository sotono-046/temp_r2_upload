# What is temp-r2-upload

- 指定したフォルダから`.md`ファイルを取得
- imgur にアップロードされたファイルを取得
- cloudflareR2 にアップロードし、URL を置き換える

# How to use

- install uv
  - [astral\-sh/uv: An extremely fast Python package and project manager, written in Rust\.](https://github.com/astral-sh/uv)
- `uv sync`
- make & set `.env`
- `uv run temp-r2-upload`
- Done！

# .env

```env
R2_API="～.r2.cloudflarestorage.com"
R2_ACCESS_KEY="～"
R2_SECRET="～"

BUCKET_NAME = "bucket-1"
IMG_FOLDER = "img/"

MD_DIRECTORY = "../_text/bucket-1/contents/"
```

- `R2_API`…Cloudflare R2 のエンドポイント
- `R2_ACCESS_KEY`…R2 のアクセスキー
- `R2_SECRET`…R2 のシークレットキー
- `BUCKET_NAME`…R2 のバケット名
- `IMG_FOLDER`…画像を格納するフォルダ名、末尾に`/` を付ける
- `MD_DIRECTORY`…Markdown ファイルを格納するディレクトリ、絶対パスで指定

- [`BUCKET_NAME`]/[`IMG_FOLDER`] に画像をアップロードする形になる。
