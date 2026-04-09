import requests
from collections import defaultdict, Counter
import json
import os
import re
import matplotlib.pyplot as plt
from datetime import datetime, timezone

# モネ風の柔らかいパステル調のカラーパレット
monet_colors = [
    "#a8c5dd", "#f5d5b5", "#d4a5a5", "#a3c1ad", "#b2d3c2",
    "#f3e1dd", "#c4b6a4", "#e7d3c8", "#ccd4bf", "#e4d8b4"
]

# リポジトリデータを取得
def fetch_repositories():
    url = 'https://api.github.com/user/repos'
    headers = {
        'Authorization': f'token {os.getenv("GITHUB_TOKEN")}'
    }
    params = {
        'per_page': 100,
        'type': 'all'
    }
    repos = []
    while url:
        response = requests.get(url, headers=headers, params=params)
        response_data = response.json()
        repos.extend(response_data)
        url = response.links.get('next', {}).get('url')
    return repos

# 各リポジトリの言語データを取得
def fetch_languages(repo):
    url = repo['languages_url']
    headers = {
        'Authorization': f'token {os.getenv("GITHUB_TOKEN")}'
    }
    response = requests.get(url, headers=headers)
    return response.json()


# リポジトリのファイルを解析
def fetch_repository_files_recursive(contents_url, headers):
    """ 指定されたURLのファイル・ディレクトリを再帰的に取得 """
    files = []
    response = requests.get(contents_url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch contents: {response.status_code}")
        return files
    
    items = response.json()
    for item in items:
        if item["type"] == "file":
            files.append(item)
        elif item["type"] == "dir":
            # ディレクトリの場合、再帰的にその中身を取得
            files.extend(fetch_repository_files_recursive(item["url"], headers))
    return files

# 全てのファイルを解析
def analyze_repository_files(repositories):
    language_data = defaultdict(lambda: {"file_count": 0, "total_steps": 0, "import_counts": Counter(),"max_steps": 0})
    headers = {'Authorization': f'token {os.getenv("GITHUB_TOKEN")}'}
    
    for repo in repositories:
        repo_name = repo['name']
        contents_url = repo.get('contents_url', '').replace('{+path}', '')
        print(f"Fetching files for repository: {repo_name}")

        # 全てのファイルを再帰的に取得
        files = fetch_repository_files_recursive(contents_url, headers)
        
        for file in files:
            if isinstance(file, dict) and file.get("type") == "file":
                file_path = file["path"]
                file_download_url = file.get("download_url")
                print(f"Analyzing file: {file_path}")

                # ファイル内容を取得
                file_response = requests.get(file_download_url, headers=headers)
                if file_response.status_code != 200:
                    print(f"Failed to download file {file_path}: {file_response.status_code}")
                    continue

                file_content = file_response.text
                language = repo.get("language", "Unknown")
                lines = file_content.splitlines()
                step_count = len(lines)

                # 更新: ファイル数、ステップ数の合計
                language_data[language]["file_count"] += 1
                language_data[language]["total_steps"] += step_count  # ここで total_steps を加算
                language_data[language]["max_steps"] = max(language_data[language]["max_steps"], step_count)  # 最大ステップ数を更新

                # import文をカウント
                imports = re.findall(r'^\s*(import\s+\w+|from\s+\w+\s+import)', file_content, re.MULTILINE)
                language_data[language]["import_counts"].update(imports)
    
    return language_data
    
# 言語使用率を「ファイル数 * ステップ数」で計算
def calculate_language_usage(language_data):
    # 各言語の total_steps の合計を計算（total_steps がない場合は 0）
    total_steps_all_languages = sum(data.get("total_steps", 0) for data in language_data.values())
    language_usage = {
        language: round((data.get("total_steps", 0) / total_steps_all_languages) * 100, 2)
        for language, data in language_data.items()
    }
    return language_usage
    
# 言語使用円環グラフを生成して保存
def save_language_pie_chart(language_usage, filename="language_usage.png"):
    labels = []
    sizes = []
    filtered_labels = []
    filtered_sizes = []
    threshold = 5  # %が5%以下のラベルを非表示にする

    # 言語データのフィルタリングとラベル設定
    for language, size in language_usage.items():
        labels.append(language)
        sizes.append(size)
        if size >= threshold:
            filtered_labels.append(f"{language} ({size}%)")
            filtered_sizes.append(size)
        else:
            filtered_labels.append("")
            filtered_sizes.append(size)

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(aspect="equal"))

    # 円環グラフの作成（擬似的に立体感を出す）
    wedges, texts = ax.pie(
        filtered_sizes,
        startangle=140,
        colors=monet_colors[:len(filtered_labels)],  # モネ風カラーパレット
        wedgeprops=dict(width=0.3, edgecolor='w')  # 3D風の立体感
    )

    # レジェンドの設定
    ax.legend(wedges, labels, title="Languages", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))

    # タイトルと見た目の調整
    ax.set_title("Language Usage Chart", pad=20, fontsize=14, fontweight="bold", color="#3f5b85")
    fig.patch.set_facecolor("#333333")  # 背景色をダークにして8ビット風に

    # 画像の保存
    plt.savefig(filename, format="png", bbox_inches="tight", transparent=True)
    plt.close()

# READMEを更新
def save_readme(language_usage, language_data):
    # 現在の日時を取得
    update_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

    with open("README.md", "w") as f:
        f.write("# Hi there 👋\n\n")
        f.write("## Stats\n")
        f.write(f">![GitHub Stats](https://github-profile-summary-cards.vercel.app/api/cards/stats?username=ciao521)\n")
        f.write("## Language Usage\n\n")
        f.write(f">[!NOTE]\n> **Last updated: {update_time}**\n\n")
        
        f.write(f">![Python](https://img.shields.io/badge/Language-Python-blue) ![C](https://img.shields.io/badge/Language-C-lightgrey) ![JavaScript](https://img.shields.io/badge/Language-JavaScript-yellow)\n")
        f.write(f">![HTML](https://img.shields.io/badge/Language-HTML-orange) ![CSS](https://img.shields.io/badge/Language-CSS-blueviolet) ![Solidity](https://img.shields.io/badge/Language-Solidity-gray)\n")
        f.write(f">![R](https://img.shields.io/badge/Language-R-lightblue) ![Node.js](https://img.shields.io/badge/Language-Node.js-green) ![Scala](https://img.shields.io/badge/Language-Scala-red) \n\n")

        f.write(f">[!CAUTION]\n> **language_usage = total_steps_languages:** \n\n")
        # 言語とその割合を記載
        for language, percentage in language_usage.items():
            f.write(f"- {language}: {percentage}%\n")
        
        f.write("\n![Language Usage Chart](language_usage.png)\n")
                # トップ3の言語の詳細を追加
        f.write("\n## Language Details (Top 3)\n")
        top_3_languages = sorted(language_usage.keys(), key=lambda x: language_usage[x], reverse=True)[:3]
        for language in top_3_languages:
            data = language_data.get(language, {"file_count": 0, "max_steps": 0, "import_counts": Counter()})
            f.write(f"\n### {language}\n")
            f.write(f"- File count: {data['file_count']}\n")
            f.write(f"- Max steps in a file: {data.get('max_steps', 'N/A')}\n")

# 言語ごとの詳細をJSONファイルに保存
def save_language_details(language_data, filename="language_details.json"):
    # Counterをリストに変換してJSONに保存可能な形式に
    formatted_data = {
        language: {
            "file_count": data["file_count"],
            "max_steps": data["max_steps"],
            "top_imports": data["import_counts"].most_common(5)
        }
        for language, data in language_data.items()
    }

    with open(filename, "w") as f:
        json.dump(formatted_data, f, indent=4)


def main():
    # リポジトリの言語使用率を取得・計算
    repositories = fetch_repositories()
    language_data = analyze_repository_files(repositories)  # language_data を取得
    language_usage = calculate_language_usage(language_data)  
    
    
    # 言語使用率データをjsonで保存
    with open("language_usage.json", "w") as f:
        json.dump(language_usage, f)
    
    # 言語使用率の円環グラフとREADMEの保存
    save_language_pie_chart(language_usage)
    save_readme(language_usage, language_data)
    
    # 言語ごとの詳細情報を保存
    save_language_details(language_data)

if __name__ == "__main__":
    main()
