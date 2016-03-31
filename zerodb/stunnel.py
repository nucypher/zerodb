import os
import tempfile
import time
import logging

from pystunnel import Stunnel

logger = logging.getLogger("zerodb.stunnel")

def log_level(rc):
    return logging.INFO if rc == 0 else logging.ERROR


class StunnelServer:

    def __init__(self, stunnel_config):
        self.stunnel_config = stunnel_config
        self.stunnel = None

    def start(self):
        """Start a new stunnel instance.
        """
        self.stunnel = Stunnel(self.stunnel_config)
        rc = self.stunnel.start()
        logger.log(log_level(rc), "StunnelServer started with rc %d (%s)" % (rc, self.stunnel_config))
        return rc

    def stop(self):
        """When start has been called, stop MUST be called as well.
        """
        if self.stunnel is not None:
            rc = self.stunnel.stop()
            self.stunnel = None
            logger.log(log_level(rc), "StunnelServer stopped with rc %d" % rc)
            return rc
        return 1


class StunnelClient:

    def __init__(self, stunnel_config):
        self.stunnel_config = stunnel_config
        self.stunnel = None

    def start(self):
        """Start a new stunnel instance.
        """
        self._create_config()
        self.stunnel = Stunnel(self.instance_config)
        rc = self.stunnel.start()
        logger.log(log_level(rc), "StunnelClient started with rc %d (%s)" % (rc, self.instance_config))
        return rc

    def stop(self):
        """When start has been called, stop MUST be called as well.
        """
        if self.stunnel is not None:
            rc = self.stunnel.stop()
            self.stunnel = None
            self._remove_config()
            logger.log(log_level(rc), "StunnelClient stopped with rc %d" % rc)
            return rc
        return 1

    def _create_config(self):
        self.temp_dir = tempfile.mkdtemp()
        self.instance_config = os.path.join(self.temp_dir, "stunnel-client.conf")
        self.instance_pid = os.path.join(self.temp_dir, "stunnel-client.pid")
        self.instance_socket = os.path.join(self.temp_dir, "stunnel-client.sock")
        lines = []
        with open(self.stunnel_config, "rt") as f:
            lines = f.readlines()
        with open(self.instance_config, "wt") as f:
            for line in lines:
                if line.startswith("pid ="):
                    f.write("pid = %s\n" % self.instance_pid)
                elif line.startswith("accept ="):
                    f.write("accept = %s\n" % self.instance_socket)
                else:
                    f.write(line)

    def _remove_config(self):
        if os.path.exists(self.instance_config):
            os.remove(self.instance_config)
        if os.path.exists(self.temp_dir):
            for x in range(10):
                if os.listdir(self.temp_dir):
                    time.sleep(1)
                else:
                    os.rmdir(self.temp_dir)
                    break
