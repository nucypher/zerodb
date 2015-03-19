from mailbox import mbox


def all():
    d = "/home/michwill/lkml"
    files = ["100000", "200000", "300000", "400000", "500000", "600000", "700000", "800000", "900000"]

    for fname in files:
        mb = mbox(d + "/" + fname)
        for message in mb.values():
            yield message.get("subject"), message.get_payload(decode=True)


if __name__ == "__main__":
    ctr = 0
    for title, text in all():
        ctr += 1
        print ctr
    print ctr
