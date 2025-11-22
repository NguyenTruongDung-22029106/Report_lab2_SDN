from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_0
from ryu.lib.packet import packet, ethernet, ether_types

class AdvancedLearningSwitch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(AdvancedLearningSwitch, self).__init__(*args, **kwargs)
        self.mac_to_port = {}  # {dpid: {mac: port}}
        self.idle_timeout = 60  # Increased timeout for complex topologies
        self.hard_timeout = 0
        self.logger.info('AdvancedLearningSwitch initialized')

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.in_port

        try:
            pkt = packet.Packet(msg.data)
            eth_pkt = pkt.get_protocols(ethernet.ethernet)
            if not eth_pkt:
                # Not an ethernet packet, flood it
                actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
            else:
                eth = eth_pkt[0]
                dst = eth.dst
                src = eth.src
                dpid = datapath.id
                self.mac_to_port.setdefault(dpid, {})

                # Check if broadcast/multicast
                is_broadcast = (dst == 'ff:ff:ff:ff:ff:ff' or 
                               dst.startswith('01:') or 
                               dst.startswith('33:33:'))

                # Learn MAC -> port (always learn source)
                self.mac_to_port[dpid][src] = in_port

                if is_broadcast:
                    # Broadcast/multicast: always flood
                    actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
                    # Install flow to reduce future packet-ins
                    match = parser.OFPMatch(dl_dst=dst, dl_src=src)
                    self.add_flow(datapath, priority=2, match=match, actions=actions,
                                  idle_timeout=self.idle_timeout, hard_timeout=self.hard_timeout)
                    self.logger.debug('Broadcast packet: DPID=%s SRC=%s DST=%s', dpid, src, dst)
                elif dst in self.mac_to_port[dpid]:
                    # Known destination: forward to specific port
                    out_port = self.mac_to_port[dpid][dst]
                    # Prevent loop: don't send back to input port
                    if out_port != in_port:
                        actions = [parser.OFPActionOutput(out_port)]
                        # Install flow entry (simplified match for better performance)
                        match = parser.OFPMatch(dl_dst=dst)
                        self.add_flow(datapath, priority=3, match=match, actions=actions,
                                      idle_timeout=self.idle_timeout, hard_timeout=self.hard_timeout)
                        self.logger.debug('Forwarding: DPID=%s %s->%s port=%s', dpid, src, dst, out_port)
                    else:
                        # Loop detected, drop packet
                        actions = []
                        self.logger.warning('Loop detected: DPID=%s port=%s', dpid, in_port)
                else:
                    # Unknown destination: flood
                    actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
                    # Install flow to reduce future packet-ins
                    match = parser.OFPMatch(dl_dst=dst, dl_src=src)
                    self.add_flow(datapath, priority=1, match=match, actions=actions,
                                  idle_timeout=self.idle_timeout, hard_timeout=self.hard_timeout)
                    self.logger.debug('Flooding: DPID=%s SRC=%s DST=%s (unknown)', dpid, src, dst)
        except Exception as e:
            self.logger.error('Error processing packet: %s', e)
            # On error, just flood
            actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None, idle_timeout=0, hard_timeout=0):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        # OpenFlow 1.0 uses actions directly, not instructions
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    actions=actions, idle_timeout=idle_timeout, hard_timeout=hard_timeout)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, actions=actions,
                                    idle_timeout=idle_timeout, hard_timeout=hard_timeout)
        datapath.send_msg(mod)

