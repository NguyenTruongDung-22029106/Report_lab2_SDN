#!/usr/bin/env python3
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel

class ComplexTopo(Topo):
    """Topo: 1 core switch, 2 pods, mỗi pod 2 access switches, 2 hosts/pod"""
    def build(self):
        # Core switch
        core = self.addSwitch('s1')

        # Pod A: s2, s3 với hosts
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')
        self.addLink(core, s2)
        self.addLink(core, s3)
        
        # Hosts cho Pod A
        h1a = self.addHost('h1a', ip='10.0.1.1')
        h2a = self.addHost('h2a', ip='10.0.1.2')
        h3a = self.addHost('h3a', ip='10.0.2.1')
        h4a = self.addHost('h4a', ip='10.0.2.2')
        
        self.addLink(s2, h1a)
        self.addLink(s2, h2a)
        self.addLink(s3, h3a)
        self.addLink(s3, h4a)

        # Pod B: s4, s5 với hosts
        s4 = self.addSwitch('s4')
        s5 = self.addSwitch('s5')
        self.addLink(core, s4)
        self.addLink(core, s5)
        
        # Hosts cho Pod B
        h1b = self.addHost('h1b', ip='10.0.3.1')
        h2b = self.addHost('h2b', ip='10.0.3.2')
        h3b = self.addHost('h3b', ip='10.0.4.1')
        h4b = self.addHost('h4b', ip='10.0.4.2')
        
        self.addLink(s4, h1b)
        self.addLink(s4, h2b)
        self.addLink(s5, h3b)
        self.addLink(s5, h4b)

# Register topology for --custom option
topos = { 'complextopo': ( lambda: ComplexTopo() ) }

def run():
    topo = ComplexTopo()
    net = Mininet(topo=topo, controller=RemoteController, switch=OVSSwitch, link=TCLink)
    net.start()
    CLI(net)
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    run()

