import bz2
import path
import re

import six

head_re = re.compile(r'\<doc id="(\d+)" url="(.*)" title="(.*)"\>')
tail = "</doc>\n"


def read_docs(dirname="wiki_sample"):
    for fname in path.path(dirname).walkfiles("*.bz2"):
        f = bz2.BZ2File(fname)
        text = None
        for line in f:
            if six.PY3:
                line = line.decode()
            if text is None:
                r = head_re.match(line)
                if r:
                    docid, url, title = r.groups()
                    text = []
            else:
                if line == tail:
                    yield {"id": docid,
                           "url": url,
                           "title": title,
                           "text": "".join(text)}
                    text = None
                else:
                    text.append(line)
        f.close()


if __name__ == "__main__":
    for doc in read_docs():
        print(doc)
