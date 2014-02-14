#---LICENSE----------------------
'''
    Copyright 2014 Travel Modelling Group, Department of Civil Engineering, University of Toronto

    This file is part of the TMG Toolbox.

    The TMG Toolbox is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    The TMG Toolbox is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with the TMG Toolbox.  If not, see <http://www.gnu.org/licenses/>.
'''
#---METADATA---------------------
'''
V4 Transit Assignment

    Authors: pkucirek

    Latest revision by: pkucirek
    
    
    Transit Assignment Tool created for GTAModel Version 4.0
        
'''
#---VERSION HISTORY
'''
    0.0.1 Created on 2014-02-04 by pkucirek
    
    0.0.2 Added a temporary impedance matrix for compatibility with Emme 4.0.8
'''

import inro.modeller as _m
import traceback as _traceback
from contextlib import contextmanager
from contextlib import nested
_MODELLER = _m.Modeller() #Instantiate Modeller once.
_util = _MODELLER.module('TMG2.Common.Utilities')
_tmgTPB = _MODELLER.module('TMG2.Common.TmgToolPageBuilder')
NullPointerException = _util.NullPointerException

##########################################################################################################

class V4_TransitAssignment(_m.Tool()):
    
    version = '0.0.1'
    tool_run_msg = ""
    number_of_tasks = 1 # For progress reporting, enter the integer number of tasks here
    
    # Tool Input Parameters
    #    Only those parameters neccessary for Modeller and/or XTMF to dock with
    #    need to be placed here. Internal parameters (such as lists and dicts)
    #    get intitialized during construction (__init__)
    
    xtmf_ScenarioNumber = _m.Attribute(int) # parameter used by XTMF only
    Scenario = _m.Attribute(_m.InstanceType) # common variable or parameter
    DemandMatrix = _m.Attribute(_m.InstanceType)
    xtmf_DemandMatrixNumber = _m.Attribute(int)
    RunTitle = _m.Attribute(str)
    
    WaitPerception = _m.Attribute(float)
    WalkPerception = _m.Attribute(float)
    BoardPerception = _m.Attribute(float)
    CongestionPerception = _m.Attribute(float)
    AssignmentPeriod = _m.Attribute(float)
    
    Iterations = _m.Attribute(int)
    NormGap = _m.Attribute(float)
    RelGap = _m.Attribute(float)
    
    def __init__(self):
        #---Init internal variables
        self.TRACKER = _util.ProgressTracker(self.number_of_tasks) #init the ProgressTracker
        
        #---Set the defaults of parameters used by Modeller
        self.Scenario = _MODELLER.scenario #Default is primary scenario
        self.DemandMatrix = _MODELLER.emmebank.matrix('mf9')
        self.WaitPerception = 1.0
        self.WalkPerception = 1.0
        self.BoardPerception = 1.0
        self.CongestionPerception = 1.0
        self.AssignmentPeriod = 1.0 / 3.0
        self.NormGap = 0.01
        self.RelGap = 0.001
        self.Iterations = 20
        
        #---Priavte flags for estimation purposes only
        self._useEmme41Beta = False
        self._headwayFraction = 0.5
        
        self._useLogitConnectorChoice = True
        self._connectorLogitScale = 0.2
        self._connectorLogitTruncation = 0.05
        
        self._congestionFunctionType = "BPR" #"CONICAL"
        self._considerTotalImpedance = True
        self._useMulticore = False
        self._exponent = 4
        
    
    def page(self):
        pb = _tmgTPB.TmgToolPageBuilder(self, title="V4 Transit Assignment v%s" %self.version,
                     description="Executes a congested transit assignment procedure \
                        for GTAModel V4.0. \
                        <br><br>Hard-coded assumptions: \
                        <ul><li> Boarding penalties are assumed stored in <b>UT3</b></li>\
                        <li> The congestion term is stored in <b>US3</b></li>\
                        <li> In-vehicle time perception is 1.0</li>\
                        <li> Unless specified, all available transit modes will be used.</li>\
                        </ul>\
                        <font color='red'>This tool is only compatible with Emme 4 and later versions</font>",
                     branding_text="TMG")
        
        if self.tool_run_msg != "": # to display messages in the page
            pb.tool_run_status(self.tool_run_msg_status)
        
        pb.add_header("SCENARIO INPUTS")
        
        pb.add_select_scenario(tool_attribute_name= 'Scenario',
                               title= 'Scenario:',
                               allow_none= False)
        
        pb.add_select_matrix(tool_attribute_name= 'DemandMatrix',
                             filter= ['FULL'], 
                             title= "Demand Matrix",
                             note= "A full matrix of OD demand")
        
        pb.add_header("PARAMETERS")
        with pb.add_table(False) as t:
            with t.table_cell():
                 pb.add_html("<b>Wait Time Perception:</b>")
            with t.table_cell():
                pb.add_text_box(tool_attribute_name= 'WaitPerception', size= 10)
            with t.table_cell():
                pb.add_html("Converts waiting minutes to impedance")
            t.new_row()
            
            with t.table_cell():
                 pb.add_html("<b>Walk Time Perception:</b>")
            with t.table_cell():
                pb.add_text_box(tool_attribute_name= 'WalkPerception', size= 10)
            with t.table_cell():
                pb.add_html("Converts walking minutes to impedance")
            t.new_row()
            
            with t.table_cell():
                 pb.add_html("<b>Boarding Perception:</b>")
            with t.table_cell():
                pb.add_text_box(tool_attribute_name= 'BoardPerception', size= 10)
            with t.table_cell():
                pb.add_html("Converts boarding impedance to impedance")
            t.new_row()
            
            with t.table_cell():
                 pb.add_html("<b>Congestion Perception:</b>")
            with t.table_cell():
                pb.add_text_box(tool_attribute_name= 'CongestionPerception', size= 10)
            with t.table_cell():
                pb.add_html("Converts congestion impedance to impedance")
            t.new_row()
            
            with t.table_cell():
                 pb.add_html("<b>Peak/Representative Hour Factor:</b>")
            with t.table_cell():
                pb.add_text_box(tool_attribute_name= 'AssignmentPeriod', size= 10)
            with t.table_cell():
                pb.add_html("Converts multiple-hour demand to a single assignment hour.")
            t.new_row()
        
        pb.add_header("CONVERGANCE CRITERIA")
        with pb.add_table(False) as t:
            with t.table_cell():
                pb.add_text_box(tool_attribute_name= 'Iterations', size= 4,
                                title= "Iterations")
            
            with t.table_cell():
                pb.add_text_box(tool_attribute_name= 'NormGap', size= 12,
                                title= "Normalized Gap")
                
            with t.table_cell():
                pb.add_text_box(tool_attribute_name= 'RelGap', size= 12,
                                title= "Relative Gap")
                
        return pb.render()
    
    ##########################################################################################################
        
    def run(self):
        self.tool_run_msg = ""
        self.TRACKER.reset()
        
        try:
            if self.AssignmentPeriod == None: raise NullPointerException("Assignment period not specified")
            if self.WaitPerception == None: raise NullPointerException("Waiting perception not specified")
            if self.WalkPerception == None: raise NullPointerException("Walking perception not specified")
            if self.BoardPerception == None: raise NullPointerException("Boarding perception not specified")
            if self.CongestionPerception == None: raise NullPointerException("Congestion perception not specified")
            if self.Iterations == None: raise NullPointerException("Maximum iterations not specified")
            if self.NormGap == None: raise NullPointerException("Normalized gap not specified")
            if self.RelGap == None: raise NullPointerException("Relative gap not specified")
            
            self._Execute()
        except Exception, e:
            self.tool_run_msg = _m.PageBuilder.format_exception(
                e, _traceback.format_exc(e))
            raise
        
        self.tool_run_msg = _m.PageBuilder.format_info("Done.")
    
    def __call__(self, xtmf_ScenarioNumber, xtmf_DemandMatrixNumber, WaitPerception,
                 WalkPerception, BoardPerception, CongestionPerception, AssignmentPeriod,
                 Iterations, NormGap, RelGap):
        
        #---1 Set up scenario
        self.Scenario = _m.Modeller().emmebank.scenario(xtmf_ScenarioNumber)
        if (self.Scenario == None):
            raise Exception("Scenario %s was not found!" %xtmf_ScenarioNumber)
        
        #---2 Set up demand matrix
        self.DemandMatrix = _MODELLER.emmebank.matrix("mf%s" %xtmf_DemandMatrixNumber)
        if self.DemandMatrix == None:
            raise Exception("Full matrix mf%s was not found!" %xtmf_DemandMatrixNumber)
        
        #---3 Set up other parameters
        self.WaitPerception = WaitPerception
        self.WalkPerception = WalkPerception
        self.BoardPerception = BoardPerception
        self.CongestionPerception = CongestionPerception
        self.AssignmentPeriod = AssignmentPeriod
        self.Iterations = Iterations
        self.NormGap = NormGap
        self.RelGap = RelGap
        
        try:
            self._Execute()
        except Exception, e:
            msg = str(e) + "\n" + _traceback.format_exc(e)
            raise Exception(msg)
    
    ##########################################################################################################    
    
    
    def _Execute(self):
        with _m.logbook_trace(name="{classname} v{version}".format(classname=(self.__class__.__name__), version=self.version),
                                     attributes=self._GetAtts()):
            
            with _util.tempMatrixMANAGER('Temp impedances') as impedanceMatrix:
                congestedAssignmentTool = _MODELLER.tool("inro.emme.transit_assignment.congested_transit_assignment")
                
                self.TRACKER.runTool(congestedAssignmentTool,
                                     transit_assignment_spec= self._GetBaseAssignmentSpec(),
                                     congestion_function= self._GetFuncSpec(),
                                     stopping_criteria= self._GetStopSpec(),
                                     impedances= impedanceMatrix,
                                     scenario= self.Scenario)

    ##########################################################################################################
    
    #----SUB FUNCTIONS---------------------------------------------------------------------------------  
    
    def _GetAtts(self):
        atts = {
                "Scenario" : "%s - %s" %(self.Scenario, self.Scenario.title),
                "Version": self.version,
                "Demand Matrix": "%s - %s" %(self.DemandMatrix, self.DemandMatrix.description),
                "Wait Perception": self.WaitPerception,
                "Walk Perception": self.WalkPerception,
                "Congestion Perception": self.CongestionPerception,
                "Assignment Period": self.AssignmentPeriod,
                "Boarding Perception": self.BoardPerception,
                "Iterations": self.Iterations,
                "Normalized Gap": self.NormGap,
                "Relative Gap": self.RelGap,
                "self": self.__MODELLER_NAMESPACE__}
            
        return atts 
    
    def _GetBaseAssignmentSpec(self):
        baseSpec = {
                "modes": ["*"],
                "demand": self.DemandMatrix.id,
                "waiting_time": {
                    "headway_fraction": self._headwayFraction,
                    "effective_headways": "hdw",
                    "spread_factor": 1,
                    "perception_factor": self.WaitPerception
                },
                "boarding_time": {
                    "at_nodes": None,
                    "on_lines": {
                        "penalty": "ut3",
                        "perception_factor": self.BoardPerception
                    }
                },
                "boarding_cost": {
                    "at_nodes": {
                        "penalty": 0,
                        "perception_factor": 1
                    },
                    "on_lines": None
                },
                "in_vehicle_time": {
                    "perception_factor": 1
                },
                "in_vehicle_cost": None,
                "aux_transit_time": {
                    "perception_factor": self.WalkPerception
                },
                "aux_transit_cost": None,
                "connector_to_connector_path_prohibition": None,
                "od_results": {
                    "total_impedance": None
                },
                "type": "EXTENDED_TRANSIT_ASSIGNMENT"
            }
        
        if self._useEmme41Beta:
            baseSpec ["flow_distribution_with_aux_transit_choices"] = {
                                    "choices_at_nodes": "LOGIT_ON_ALL_CONNECTORS",
                                    "logit_parameters": {
                                        "scale": self._connectorLogitScale,
                                        "truncation": self._connectorLogitTruncation
                                    },
                                    "alighting_choices": None,
                                    "fixed_proportions_on_connectors": None
                                }
            baseSpec['flow_distribution_between_lines'] = {
                    "consider_total_impedance": self._considerTotalImpedance
                }
        else:
            baseSpec['flow_distribution_at_origins'] = {
                                                        "by_time_to_destination": {
                                                        "logit": {
                                                            "scale": self._connectorLogitScale,
                                                            "truncation": self._connectorLogitTruncation
                                                        }
                                                    },
                                                    "by_fixed_proportions": None}
            baseSpec['flow_distribution_between_lines'] = {
                                        "consider_travel_time": self._considerTotalImpedance
                                    }
            baseSpec['save_strategies'] = True
        
        if self._useMulticore:
            baseSpec["performance_settings"] = {"number_of_processors": 8}
        
        return baseSpec
        #return str(baseSpec) #The tool is expecting this as a string, not a dict
    
    def _GetFuncSpec(self):
        funcSpec = {
                    "type": self._congestionFunctionType,
                    "weight": self.CongestionPerception,
                    "exponent": self._exponent,
                    "assignment_period": self.AssignmentPeriod,
                    "orig_func": False,
                    "congestion_attribute": "us3" #Hard-coded to US3
                    }
        
        return funcSpec
    
    def _GetStopSpec(self):
        stopSpec = {
                    "max_iterations": self.Iterations,
                    "normalized_gap": self.NormGap,
                    "relative_gap": self.RelGap
                    }
        return stopSpec
    
    @_m.method(return_type=_m.TupleType)
    def percent_completed(self):
        return self.TRACKER.getProgress()
                
    @_m.method(return_type=unicode)
    def tool_run_msg_status(self):
        return self.tool_run_msg
        