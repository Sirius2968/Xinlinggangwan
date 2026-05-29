"""
MCP 工具实现 —— 仅保留需要连接外部接口的工具
PubMed 学术文献查询是 MCP 对外暴露的核心能力
"""

import urllib.request
import urllib.parse
import json
import xml.etree.ElementTree as ET


def search_psychology_literature(query: str, max_results: int = 5) -> str:
    """
    查询 PubMed 数据库中与心理健康相关的学术文献。
    返回文献标题、作者、期刊和发表日期，并附带 PubMed 链接。
    通过美国国立医学图书馆的 E-utilities API（免费公开接口）。
    """
    if max_results > 10:
        max_results = 10
    if max_results < 1:
        max_results = 1

    try:
        # Step 1: 搜索 PubMed，获取文献 ID 列表
        search_params = urllib.parse.urlencode({
            "db": "pubmed",
            "term": f"(mental health OR psychology OR psychotherapy) AND {query}",
            "retmax": str(max_results),
            "retmode": "json",
            "sort": "relevance",
        })
        search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?{search_params}"
        req = urllib.request.Request(search_url, headers={"User-Agent": "XinLingGangWan/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            search_data = json.loads(resp.read())

        id_list = search_data.get("esearchresult", {}).get("idlist", [])
        if not id_list:
            return f"未找到关于「{query}」的学术文献。建议尝试更宽泛的搜索词。"

        # Step 2: 根据 ID 获取文献摘要信息
        fetch_params = urllib.parse.urlencode({
            "db": "pubmed",
            "id": ",".join(id_list),
            "retmode": "xml",
        })
        fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?{fetch_params}"
        req = urllib.request.Request(fetch_url, headers={"User-Agent": "XinLingGangWan/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_data = resp.read()

        root = ET.fromstring(xml_data)
        articles = []
        for article in root.findall(".//PubmedArticle"):
            title_elem = article.find(".//ArticleTitle")
            title = title_elem.text or "(无标题)" if title_elem is not None else "(无标题)"

            authors = []
            for author in article.findall(".//Author"):
                last = author.find("./LastName")
                fore = author.find("./ForeName")
                if last is not None and last.text:
                    name = last.text
                    if fore is not None and fore.text:
                        name += " " + fore.text
                    authors.append(name)
            author_str = ", ".join(authors[:3])
            if len(authors) > 3:
                author_str += f" 等{len(authors)}人"

            journal_elem = article.find(".//Journal/Title")
            journal = journal_elem.text if journal_elem is not None and journal_elem.text else "Unknown"

            year_elem = article.find(".//PubDate/Year")
            year = year_elem.text if year_elem is not None else "?"

            pmid_elem = article.find(".//PMID")
            pmid = pmid_elem.text if pmid_elem is not None and pmid_elem.text else ""

            articles.append({
                "title": title,
                "authors": author_str or "未知作者",
                "journal": journal,
                "year": year,
                "pmid": pmid,
            })

        if not articles:
            return f"未能解析到关于「{query}」的文献详细信息。"

        lines = [f"关于「{query}」的学术文献（来自 PubMed）：\n"]
        for i, art in enumerate(articles, 1):
            lines.append(
                f"{i}. {art['title']}\n"
                f"   作者: {art['authors']}\n"
                f"   期刊: {art['journal']} ({art['year']})\n"
                f"   PubMed: https://pubmed.ncbi.nlm.nih.gov/{art['pmid']}/\n"
            )

        return "\n".join(lines)

    except urllib.error.URLError as e:
        return f"无法连接到 PubMed 学术数据库：网络连接失败。请检查网络后重试。"
    except Exception as e:
        return f"查询学术文献时发生错误：{str(e)}。请稍后重试。"


# MCP 工具注册表
TOOL_REGISTRY = {
    "search_psychology_literature": search_psychology_literature,
}
