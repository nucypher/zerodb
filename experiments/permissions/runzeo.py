from zeopermissions import register_auth
from ZEO.runzeo import ZEOOptions
from ZEO.runzeo import ZEOServer


def main(args=None):
    register_auth()
    options = ZEOOptions()
    options.realize(args=["-C", "zeo.config"])
    s = ZEOServer(options)
    s.main()


if __name__ == "__main__":
    main()
