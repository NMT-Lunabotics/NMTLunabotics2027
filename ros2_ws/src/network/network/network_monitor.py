#!/usr/bin/env python3
import math, os, re, subprocess, threading, time, rclpy, yaml
from ament_index_python.packages import get_package_share_directory
from rcl_interfaces.msg import SetParametersResult
from rclpy.node import Node
from rclpy.parameter import Parameter
from robot_interfaces.msg import NetworkStatus

class NetworkMonitor(Node):
    def __init__(self):
        super().__init__("network_monitor")
        # Package start message
        self.get_logger().info("\033[94mNetwork monitor node started\033[0m")

        network_config=os.path.join(get_package_share_directory("network"), "config", "network_monitor.yaml")
        self.declare_parameter("network_config", network_config)
        with open(self.get_parameter("network_config").value, "r") as file: data=yaml.safe_load(file)
        self.persisted=set()
        self.declare_flatend_params(data["network_monitor"]["ros__parameters"])

        self.declare_parameter("persistent", True)
        self.persistent=self.get_parameter("persistent").value
        self.declare_parameter("persistent_type", "global")
        self.persistent_type=self.get_parameter("persistent_type").value

        self.units={
            "tx_rate": {"kbps": 1e3, "mbps": 1e6},
            "rx_rate": {"kbps": 1e3, "mbps": 1e6},
            "avg_bandwidth": {"kbps": 1e3, "mbps": 1e6},
            "total_bandwidth": {"kb": 1e3, "mb": 1e6, "gb": 1e9},
        }

        self.avg_start=time.monotonic()
        self.avg_bytes=0
        self.last=None
        self.total_rx=0
        self.total_tx=0
        self.rx_bps=0.0
        self.tx_bps=0.0
        self.latency=-1.0
        self.running=True
        self.publisher=None
        self.timer=None

        self.rebuild_publisher(self.get_parameter("topic").value)
        self.rebuild_timer(self.get_parameter("update_rate").value)

        self.add_on_set_parameters_callback(self.on_params_change)

        self.worker=threading.Thread(target=self.latency_loop, daemon=True)
        self.worker.start()

        # Network monitor attach
        self.get_logger().info(f"\033[92mAttached to {self.get_parameter('interface').value}, {self.get_parameter('target_host').value}: Connected\033[0m")

    def on_params_change(self, params):
        for param in params:
            if param.name=="persistent": self.persistent=param.value
            if param.name=="persistent_type": self.persistent_type=param.value
            if param.name=="update_rate": self.rebuild_timer(param.value)
            if param.name=="topic": self.rebuild_publisher(param.value)
            if param.name=="interface": self.last=None; self.rx_bps=self.tx_bps=0.0
            if param.name=="avg_bandwidth.reset" and param.value: self.reset_average()
            if param.name=="total_bandwidth.reset" and param.value: self.total_rx=self.total_tx=0; self.reset_average()

        if not self.persistent: return SetParametersResult(successful=True)
        if not any(param.name in self.persisted for param in params): return SetParametersResult(successful=True)

        config_path=self.get_parameter("network_config").value
        config_paths=[config_path]
        if self.persistent_type=="global" and "/install/" in config_path: config_paths.append(os.path.join(config_path.split("/install/")[0], "src", "network", "config", "network_monitor.yaml"))

        for path in dict.fromkeys(os.path.realpath(path) for path in config_paths):
            if not os.path.exists(path): continue
            with open(path, "r") as file: old_text=file.read()
            data=yaml.safe_load(old_text)
            for param in params:
                if param.name not in self.persisted: continue
                node=data["network_monitor"]["ros__parameters"]
                *parents, leaf=param.name.split(".")
                for key in parents: node=node.setdefault(key, {})
                node[leaf]=param.value
            above, inline, index={}, {}, 0

            for line in old_text.splitlines():
                if line.strip().startswith("#"): above.setdefault(index, []).append(line.strip())
                elif line.strip() and not line.strip().startswith("-"):
                    if " #" in line: inline[index]=line[line.index(" #"):].strip()
                    index+=1
            output, index=[], 0
            for line in yaml.safe_dump(data, sort_keys=False).splitlines():
                if line.strip().startswith("-"): output.append(line); continue
                output+=[" "*(len(line)-len(line.lstrip()))+text for text in above.get(index, [])]
                output.append(f"{line:<50} {inline[index]}" if index in inline else line)
                index+=1
            with open(path, "w") as file: file.write("\n".join(output)+"\n")
        return SetParametersResult(successful=True)

    def declare_flatend_params(self, value, path=""):
        if isinstance(value, dict):
            for param_key, param_value in value.items(): self.declare_flatend_params(param_value, f"{path}{param_key}.")
        else:
            full_path=path.rstrip(".")
            self.persisted.add(full_path)
            if not self.has_parameter(full_path): self.declare_parameter(full_path, value)

    def rebuild_publisher(self, topic):
        if self.publisher: self.destroy_publisher(self.publisher)
        self.publisher=self.create_publisher(NetworkStatus, topic, 10)

    def rebuild_timer(self, rate):
        if self.timer: self.destroy_timer(self.timer)
        self.timer=self.create_timer(1.0/float(rate), self.tick)

    def reset_average(self):
        self.avg_start=time.monotonic()
        self.avg_bytes=0

    def latency_loop(self):
        while self.running:
            started=time.monotonic()
            if self.get_parameter("latency.enabled").value:
                timeout=float(self.get_parameter("ping_timeout").value)
                result=subprocess.run(["ping", "-c", "1", "-W", str(max(1, math.ceil(timeout))), self.get_parameter("target_host").value], capture_output=True, text=True)
                match=re.search(r"time[=<]([\d.]+)\s*ms", result.stdout)
                self.latency=float(match.group(1)) if match else -1.0
            time.sleep(max(0.0, 1.0/float(self.get_parameter("ping_rate").value)-(time.monotonic()-started)))

    def scaled(self, metric, raw):
        if not self.get_parameter(f"{metric}.enabled").value: return math.nan, ""
        unit=self.get_parameter(f"{metric}.unit").value
        return raw/self.units[metric][unit], unit

    def tick(self):
        now=time.monotonic()
        interface=self.get_parameter("interface").value
        counters=None
        with open("/proc/net/dev") as file:
            for line in file:
                name, _, data=line.partition(":")
                if name.strip()==interface: fields=data.split(); counters=(int(fields[0]), int(fields[8]))

        if counters is None:
            self.last=None
            self.rx_bps=self.tx_bps=0.0
            self.get_logger().warn(f"Interface '{interface}' not found", throttle_duration_sec=5.0)
        else:
            rx, tx=counters
            if self.last:
                dt=now-self.last[2]
                d_rx, d_tx=rx-self.last[0], tx-self.last[1]
                if d_rx>=0 and d_tx>=0:
                    self.rx_bps=d_rx*8/dt
                    self.tx_bps=d_tx*8/dt
                    self.total_rx+=d_rx
                    self.total_tx+=d_tx
                    self.avg_bytes+=d_rx+d_tx
            self.last=(rx, tx, now)

        elapsed=now-self.avg_start
        total_bytes=self.total_rx+self.total_tx
        avg_bps=self.avg_bytes*8/elapsed if elapsed>0 else 0.0

        msg=NetworkStatus()
        msg.latency=float(self.latency) if self.get_parameter("latency.enabled").value else math.nan
        msg.tx_rate, msg.tx_rate_units=self.scaled("tx_rate", self.tx_bps)
        msg.rx_rate, msg.rx_rate_units=self.scaled("rx_rate", self.rx_bps)
        msg.avg_bandwidth, msg.avg_bandwidth_units=self.scaled("avg_bandwidth", avg_bps)
        msg.total_bandwidth, msg.total_bandwidth_units=self.scaled("total_bandwidth", total_bytes)
        self.publisher.publish(msg)

        for name in ("avg_bandwidth.reset", "total_bandwidth.reset"):
            if self.get_parameter(name).value: self.set_parameters([Parameter(name, Parameter.Type.BOOL, False)])

    def destroy_node(self):
        self.running=False
        super().destroy_node()

def main():
    rclpy.init()
    node=NetworkMonitor()
    try: rclpy.spin(node)
    except KeyboardInterrupt: pass
    finally:
        node.destroy_node()
        if rclpy.ok(): rclpy.shutdown()

if __name__=="__main__":
    main()