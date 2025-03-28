"""
==========================================================================
MeshMultiCgraRTL_test.py
==========================================================================
Test cases for multi-CGRA with mesh NoC.

Author : Cheng Tan
  Date : Jan 8, 2024
"""

from pymtl3.passes.backends.verilog import (VerilogVerilatorImportPass)
from pymtl3.stdlib.test_utils import (run_sim,
                                      config_model_with_cmdline_opts)

from ..MeshMultiCgraRTL import MeshMultiCgraRTL
from ...fu.flexible.FlexibleFuRTL import FlexibleFuRTL
from ...fu.single.AdderRTL import AdderRTL
from ...fu.single.BranchRTL import BranchRTL
from ...fu.single.CompRTL import CompRTL
from ...fu.single.LogicRTL import LogicRTL
from ...fu.single.MemUnitRTL import MemUnitRTL
from ...fu.single.MulRTL import MulRTL
from ...fu.single.PhiRTL import PhiRTL
from ...fu.single.SelRTL import SelRTL
from ...fu.single.ShifterRTL import ShifterRTL
from ...fu.vector.VectorAdderComboRTL import VectorAdderComboRTL
from ...fu.vector.VectorMulComboRTL import VectorMulComboRTL
from ...lib.basic.val_rdy.SinkRTL import SinkRTL as TestSinkRTL
from ...lib.basic.val_rdy.SourceRTL import SourceRTL as TestSrcRTL
from ...lib.cmd_type import *
from ...lib.messages import *
from ...lib.opt_type import *


#-------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------

class TestHarness(Component):
  def construct(s, DUT, FunctionUnit, FuList, DataType, PredicateType,
                CtrlPktType, CtrlSignalType, NocPktType, CmdType,
                cgra_rows, cgra_columns, width, height, ctrl_mem_size,
                data_mem_size_global, data_mem_size_per_bank,
                num_banks_per_cgra, num_registers_per_reg_bank,
                src_ctrl_pkt, ctrl_steps, controller2addr_map, complete_signal_sink_out):

    s.num_terminals = cgra_rows * cgra_columns
    s.num_tiles = width * height

    s.src_ctrl_pkt = TestSrcRTL(CtrlPktType, src_ctrl_pkt)
    s.complete_signal_sink_out = TestSinkRTL(CtrlPktType, complete_signal_sink_out)

    s.dut = DUT(DataType, PredicateType, CtrlPktType, CtrlSignalType,
                NocPktType, CmdType, cgra_rows, cgra_columns,
                height, width, ctrl_mem_size, data_mem_size_global,
                data_mem_size_per_bank, num_banks_per_cgra,
                num_registers_per_reg_bank, ctrl_steps, ctrl_steps,
                FunctionUnit, FuList, controller2addr_map)

    # Connections
    s.src_ctrl_pkt.send //= s.dut.recv_from_cpu_pkt
    s.complete_signal_sink_out.recv //= s.dut.send_to_cpu_pkt

  def done(s):
    return s.src_ctrl_pkt.done() and s.complete_signal_sink_out.done()

  def line_trace(s):
    return s.dut.line_trace()

def test_homo_2x2_2x2(cmdline_opts):
  num_tile_inports  = 4
  num_tile_outports = 4
  num_fu_inports = 4
  num_fu_outports = 2
  num_routing_outports = num_tile_outports + num_fu_inports
  ctrl_mem_size = 16
  data_mem_size_global = 128
  data_mem_size_per_bank = 4
  num_banks_per_cgra = 2
  cgra_rows = 2
  cgra_columns = 2
  num_terminals = cgra_rows * cgra_columns
  x_tiles = 2
  y_tiles = 2
  TileInType = mk_bits(clog2(num_tile_inports + 1))
  FuInType = mk_bits(clog2(num_fu_inports + 1))
  FuOutType = mk_bits(clog2(num_fu_outports + 1))
  ctrl_addr_nbits = clog2(ctrl_mem_size)
  data_addr_nbits = clog2(data_mem_size_global)
  DataAddrType = mk_bits(clog2(data_mem_size_global))
  num_tiles = x_tiles * y_tiles
  DUT = MeshMultiCgraRTL
  FunctionUnit = FlexibleFuRTL
  FuList = [AdderRTL,
            MulRTL,
            LogicRTL,
            ShifterRTL,
            PhiRTL,
            CompRTL,
            BranchRTL,
            MemUnitRTL,
            SelRTL,
            VectorMulComboRTL,
            VectorAdderComboRTL]
  data_nbits = 32
  predicate_nbits = 1
  DataType = mk_data(data_nbits, 1)
  PredicateType = mk_predicate(1, 1)
  cmd_nbits = clog2(NUM_CMDS)
  num_registers_per_reg_bank = 16
  CmdType = mk_bits(cmd_nbits)
  per_cgra_data_size = int(data_mem_size_global / num_terminals)
  controller2addr_map = {}
  for i in range(num_terminals):
    controller2addr_map[i] = [i * per_cgra_data_size,
                              (i + 1) * per_cgra_data_size - 1]

  cmd_nbits = clog2(NUM_CMDS)
  num_registers_per_reg_bank = 16
  CmdType = mk_bits(cmd_nbits)

  cgra_id_nbits = clog2(num_terminals)
  addr_nbits = clog2(data_mem_size_global)

  CtrlPktType = \
        mk_intra_cgra_pkt(num_tiles,
                          cgra_id_nbits,
                          NUM_CMDS,
                          ctrl_mem_size,
                          NUM_OPTS,
                          num_fu_inports,
                          num_fu_outports,
                          num_tile_inports,
                          num_tile_outports,
                          num_registers_per_reg_bank,
                          addr_nbits,
                          data_nbits,
                          predicate_nbits)
  CtrlSignalType = \
      mk_separate_reg_ctrl(NUM_OPTS,
                           num_fu_inports,
                           num_fu_outports,
                           num_tile_inports,
                           num_tile_outports,
                           num_registers_per_reg_bank)
  NocPktType = mk_multi_cgra_noc_pkt(ncols = cgra_columns,
                                     nrows = cgra_rows,
                                     ntiles = num_tiles,
                                     addr_nbits = data_addr_nbits,
                                     data_nbits = data_nbits,
                                     predicate_nbits = predicate_nbits,
                                     ctrl_actions = NUM_CMDS,
                                     ctrl_mem_size = ctrl_mem_size,
                                     ctrl_operations = NUM_OPTS,
                                     ctrl_fu_inports = num_fu_inports,
                                     ctrl_fu_outports = num_fu_outports,
                                     ctrl_tile_inports = num_tile_inports,
                                     ctrl_tile_outports = num_tile_outports)
  pickRegister = [FuInType(x + 1) for x in range(num_fu_inports)]
  src_opt_per_tile = [[
                # cgra_id src dst vc_id opq cmd_type    addr operation predicate
      CtrlPktType(0,      0,  i,  0,    0,  CMD_CONFIG, 0,   OPT_INC,  b1(0),
                  pickRegister,
                  [TileInType(4), TileInType(3), TileInType(2), TileInType(1),
                   # TODO: make below as TileInType(5) to double check.
                   TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                  
                  [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                   FuOutType(1), FuOutType(1), FuOutType(1), FuOutType(1)], 0, 0, 0, 0, 0),

      CtrlPktType(0,      0,  i,  0,    0,  CMD_CONFIG, 1,   OPT_INC, b1(0),
                  pickRegister,
                  [TileInType(4), TileInType(3), TileInType(2), TileInType(1),
                   TileInType(0), TileInType(0), TileInType(0), TileInType(0)],
                  
                  [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                   FuOutType(1), FuOutType(1), FuOutType(1), FuOutType(1)], 0, 0, 0, 0, 0),

      CtrlPktType(0,      0,  i,  0,    0,  CMD_CONFIG, 2,   OPT_ADD, b1(0),
                  pickRegister,
                  [TileInType(4), TileInType(3), TileInType(2), TileInType(1),
                   TileInType(0), TileInType(0), TileInType(0), TileInType(0)],

                  [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                   FuOutType(1), FuOutType(1), FuOutType(1), FuOutType(1)], 0, 0, 0, 0, 0),

      CtrlPktType(0,      0,  i,  0,    0,  CMD_CONFIG, 3,   OPT_STR, b1(0),
                  pickRegister,
                  [TileInType(4), TileInType(3), TileInType(2), TileInType(1),
                   TileInType(0), TileInType(0), TileInType(0), TileInType(0)],

                  [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                   FuOutType(1), FuOutType(1), FuOutType(1), FuOutType(1)], 0, 0, 0, 0, 0),

      CtrlPktType(0,      0,  i,  0,    0,  CMD_CONFIG, 4,   OPT_ADD, b1(0),
                  pickRegister,
                  [TileInType(4), TileInType(3), TileInType(2), TileInType(1),
                   TileInType(0), TileInType(0), TileInType(0), TileInType(0)],

                  [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                   FuOutType(1), FuOutType(1), FuOutType(1), FuOutType(1)], 0, 0, 0, 0, 0),

      CtrlPktType(0,      0,  i,  0,    0,  CMD_CONFIG, 5,   OPT_ADD, b1(0),
                  pickRegister,
                  [TileInType(4), TileInType(3), TileInType(2), TileInType(1),  
                   TileInType(0), TileInType(0), TileInType(0), TileInType(0)],

                  [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                   FuOutType(1), FuOutType(1), FuOutType(1), FuOutType(1)], 0, 0, 0, 0, 0),

      # This last one is for launching kernel.
      CtrlPktType(0,      0,  i,  0,    0,  CMD_LAUNCH, 0,   OPT_ADD, b1(0),
                  pickRegister,
                  [TileInType(4), TileInType(3), TileInType(2), TileInType(1),
                   TileInType(0), TileInType(0), TileInType(0), TileInType(0)],

                  [FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0),
                   FuOutType(1), FuOutType(1), FuOutType(1), FuOutType(1)], 0, 0, 0, 0, 0)
      ] for i in range(num_tiles)]
  #                                       cgra_id, src,       dst, opaque, vc, ctrl_action
  complete_signal_sink_out = [CtrlPktType(      0,   0, num_tiles,      0,  1, ctrl_action = CMD_COMPLETE)]

  src_ctrl_pkt = []
  for opt_per_tile in src_opt_per_tile:
    src_ctrl_pkt.extend(opt_per_tile)

  th = TestHarness(DUT, FunctionUnit, FuList, DataType, PredicateType, CtrlPktType,
                   CtrlSignalType, NocPktType, CmdType, cgra_rows, cgra_columns,
                   x_tiles, y_tiles, ctrl_mem_size, data_mem_size_global,
                   data_mem_size_per_bank, num_banks_per_cgra,
                   num_registers_per_reg_bank, src_ctrl_pkt,
                   ctrl_mem_size, controller2addr_map, complete_signal_sink_out)
  th.elaborate()
  th.dut.set_metadata(VerilogVerilatorImportPass.vl_Wno_list,
                      ['UNSIGNED', 'UNOPTFLAT', 'WIDTH', 'WIDTHCONCAT',
                       'ALWCOMBORDER'])
  th = config_model_with_cmdline_opts(th, cmdline_opts, duts = ['dut'])
  run_sim(th)

