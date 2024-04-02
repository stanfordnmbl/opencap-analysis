"""
    ---------------------------------------------------------------------------
    OpenCap processing: squat_analysis.py
    ---------------------------------------------------------------------------

    Copyright 2024 Stanford University and the Authors
    
    Author(s): Antoine Falisse, Carmichael Ong
    
    Licensed under the Apache License, Version 2.0 (the "License"); you may not
    use this file except in compliance with the License. You may obtain a copy
    of the License at http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
 
import sys
sys.path.append('../')

import numpy as np
import pandas as pd
from scipy.signal import find_peaks
from matplotlib import pyplot as plt

from utilsKinematics import kinematics


class squat_analysis(kinematics):
    
    def __init__(self, session_dir, trial_name, n_repetitions=-1,
                 lowpass_cutoff_frequency_for_coordinate_values=-1,
                 trimming_start=0, trimming_end=0):
        
        # Inherit init from kinematics class.
        super().__init__(
            session_dir, 
            trial_name, 
            lowpass_cutoff_frequency_for_coordinate_values=lowpass_cutoff_frequency_for_coordinate_values)
        
        # We might want to trim the start/end of the trial to remove bad data.
        self.trimming_start = trimming_start
        self.trimming_end = trimming_end
                        
        # Marker data load and filter.
        self.markerDict = self.get_marker_dict(
            session_dir, 
            trial_name, 
            lowpass_cutoff_frequency = lowpass_cutoff_frequency_for_coordinate_values)

        # Coordinate values.
        self.coordinateValues = self.get_coordinate_values()

        # Making sure time vectors of marker and coordinate data are the same.
        if not np.allclose(self.markerDict['time'], self.coordinateValues['time'], atol=.001, rtol=0):
            raise Exception('Time vectors of marker and coordinate data are not the same.')
        
        # Trim marker data and coordinate values.
        if self.trimming_start > 0:
            self.idx_trim_start = np.where(np.round(self.markerDict['time'] - self.trimming_start,6) <= 0)[0][-1]
            self.markerDict['time'] = self.markerDict['time'][self.idx_trim_start:,]
            for marker in self.markerDict['markers']:
                self.markerDict['markers'][marker] = self.markerDict['markers'][marker][self.idx_trim_start:,:]
            self.coordinateValues = self.coordinateValues.iloc[self.idx_trim_start:]
        
        if self.trimming_end > 0:
            self.idx_trim_end = np.where(np.round(self.markerDict['time'],6) <= np.round(self.markerDict['time'][-1] - self.trimming_end,6))[0][-1] + 1
            self.markerDict['time'] = self.markerDict['time'][:self.idx_trim_end,]
            for marker in self.markerDict['markers']:
                self.markerDict['markers'][marker] = self.markerDict['markers'][marker][:self.idx_trim_end,:]
            self.coordinateValues = self.coordinateValues.iloc[:self.idx_trim_end]
        
        # Segment squat repetitions.
        self.squatEvents = self.segment_squat(n_repetitions=n_repetitions)
        self.nRepetitions = np.shape(self.squatEvents['eventIdxs'])[0]
        
        # Initialize variables to be lazy loaded.
        self._comValues = None
        
        # Time
        self.time = self.coordinateValues['time'].to_numpy()
    
    # Compute COM trajectory.
    def comValues(self):
        if self._comValues is None:
            self._comValues = self.get_center_of_mass_values()
            if self.trimming_start > 0:
                self._comValues = self._comValues.iloc[self.idx_trim_start:]            
            if self.trimming_end > 0:
                self._comValues = self._comValues.iloc[:self.idx_trim_end]
        return self._comValues
    
    def get_squat_events(self):
        
        return self.squatEvents
    
    def compute_scalars(self, scalarNames, return_all=False):
               
        # Verify that scalarNames are methods in squat_analysis.
        method_names = [func for func in dir(self) if callable(getattr(self, func))]
        possibleMethods = [entry for entry in method_names if 'compute_' in entry]
        
        if scalarNames is None:
            print('No scalars defined, these methods are available:')
            print(*possibleMethods)
            return
        
        nonexistant_methods = [entry for entry in scalarNames if 'compute_' + entry not in method_names]
        
        if len(nonexistant_methods) > 0:
            raise Exception(str(['compute_' + a for a in nonexistant_methods]) + ' does not exist in gait_analysis class.')
        
        scalarDict = {}
        for scalarName in scalarNames:
            thisFunction = getattr(self, 'compute_' + scalarName)
            scalarDict[scalarName] = {}
            (scalarDict[scalarName]['value'],
                scalarDict[scalarName]['units']) = thisFunction(return_all=return_all)
        
        return scalarDict
    
    def segment_squat(self, n_repetitions=-1, height_value=0.2, visualizeSegmentation=False):

        pelvis_ty = self.coordinateValues['pelvis_ty'].to_numpy()  
        dt = np.mean(np.diff(self.time))

        # Identify minimums.
        pelvSignal = np.array(-pelvis_ty - np.min(-pelvis_ty))
        pelvSignalPos = np.array(pelvis_ty - np.min(pelvis_ty))
        idxMinPelvTy,_ = find_peaks(pelvSignal, distance=.7/dt, height=height_value)
        
        # Find the max adjacent to all of the minimums.
        minIdxOld = 0
        startEndIdxs = []
        for i, minIdx in enumerate(idxMinPelvTy):
            if i < len(idxMinPelvTy) - 1:
                nextIdx = idxMinPelvTy[i+1]
            else:
                nextIdx = len(pelvSignalPos)
            startIdx = np.argmax(pelvSignalPos[minIdxOld:minIdx]) + minIdxOld
            endIdx = np.argmax(pelvSignalPos[minIdx:nextIdx]) + minIdx
            startEndIdxs.append([startIdx,endIdx])
            minIdxOld = np.copy(minIdx)            
            
        # Limit the number of repetitions.
        if n_repetitions != -1:
            startEndIdxs = startEndIdxs[-n_repetitions:]
            
        # Extract events: start and end of each repetition.
        eventIdxs = np.array(startEndIdxs)
        eventTimes = self.time[eventIdxs]            
        
        if visualizeSegmentation:
            plt.figure()     
            plt.plot(-pelvSignal)
            for c_v, val in enumerate(startEndIdxs):
                plt.plot(val, -pelvSignal[val], marker='o', markerfacecolor='k',
                        markeredgecolor='none', linestyle='none',
                        label='Start/End rep')
                if c_v == 0:
                    plt.legend()
            plt.xlabel('Frames')
            plt.ylabel('Position [m]')
            plt.title('Vertical pelvis position')
            plt.draw()
            
        # Output.
        squatEvents = {
            'eventIdxs': startEndIdxs,
            'eventTimes': eventTimes,
            'eventNames':['repStart','repEnd']}
        
        return squatEvents
    
    def compute_peak_angle(self, coordinate, peak_type="maximum", return_all=False):
        
        # Verify that the coordinate exists.
        if coordinate not in self.coordinateValues.columns:
            raise Exception(coordinate + ' does not exist in coordinate values. Verify the name of the coordinate.')
        
        # Compute max angle for each repetition.
        peak_angles = np.zeros((self.nRepetitions))
        for i in range(self.nRepetitions):            
            rep_range = self.squatEvents['eventIdxs'][i] 
            if peak_type == "maximum":           
                peak_angles[i] = np.max(self.coordinateValues[coordinate].to_numpy()[rep_range[0]:rep_range[1]+1])
            elif peak_type == "minimum":
                peak_angles[i] = np.min(self.coordinateValues[coordinate].to_numpy()[rep_range[0]:rep_range[1]+1])
            else:
                raise Exception('peak_type must be "maximum" or "minimum".')
        
        # Average across all strides.
        peak_angle_mean = np.mean(peak_angles)
        peak_angle_std = np.std(peak_angles)
        
        # Define units.
        units = 'deg'
        
        if return_all:
            return peak_angles, units
        else:
            return peak_angle_mean, peak_angle_std, units
        
    def compute_ratio_peak_angle(self, coordinate_a, coordinate_b, peak_type="maximum", return_all=False):

        peak_angles_a, units_a = self.compute_peak_angle(coordinate_a, peak_type=peak_type, return_all=True)
        peak_angles_b, units_b = self.compute_peak_angle(coordinate_b, peak_type=peak_type, return_all=True)

        # Verify that units are the same.
        if units_a != units_b:
            raise Exception('Units of the two coordinates are not the same.')

        ratio_angles = np.zeros((self.nRepetitions))
        for i in range(self.nRepetitions):
            ratio_angles[i] = peak_angles_a[i] / peak_angles_b[i] * 100

        # Average across all strides.
        ratio_angle_mean = np.mean(ratio_angles)
        ratio_angle_std = np.std(ratio_angles)

        # Define units 
        units = '%'
        
        if return_all:
            return ratio_angles, units
        else:
            return ratio_angle_mean, ratio_angle_std, units
        
    def compute_range_of_motion(self, coordinate, return_all=False):

        # Verify that the coordinate exists.
        if coordinate not in self.coordinateValues.columns:
            raise Exception(coordinate + ' does not exist in coordinate values. Verify the name of the coordinate.')
        
        # Compute max angle for each repetition.
        ranges_of_motion = np.zeros((self.nRepetitions))
        for i in range(self.nRepetitions):            
            rep_range = self.squatEvents['eventIdxs'][i]       
            ranges_of_motion[i] = (np.max(self.coordinateValues[coordinate].to_numpy()[rep_range[0]:rep_range[1]+1]) - 
                                   np.min(self.coordinateValues[coordinate].to_numpy()[rep_range[0]:rep_range[1]+1]))
        
        # Average across all strides.
        range_of_motion_mean = np.mean(ranges_of_motion)
        range_of_motion_std = np.std(ranges_of_motion)
        
        # Define units.
        units = 'deg'
        
        if return_all:
            return ranges_of_motion, units
        else:
            return range_of_motion_mean, range_of_motion_std, units
    
    def get_coordinates_segmented(self):
        
        colNames = self.coordinateValues.columns
        data = self.coordinateValues.to_numpy(copy=True)        
        coordValuesSegmented = []
        for eventIdx in self.squatEvents['eventIdxs']:
            coordValuesSegmented.append(pd.DataFrame(data=data[eventIdx[0]:eventIdx[1]], columns=colNames))
        
        return coordValuesSegmented
    
    def get_center_of_mass_values_segmented(self):

        data = np.vstack((self.comValues()['x'],self.comValues()['y'],self.comValues()['z'])).T        
        colNames = ['com_x', 'com_y', 'com_z']        
        comValuesSegmented = []
        for eventIdx in self.squatEvents['eventIdxs']:
            comValuesSegmented.append(pd.DataFrame(data=data[eventIdx[0]:eventIdx[1]], columns=colNames))
        
        return comValuesSegmented
    
    def get_coordinates_segmented_normalized_time(self):
        
        colNames = self.coordinateValues.columns
        data = self.coordinateValues.to_numpy(copy=True)        
        coordValuesSegmentedNorm = []
        for eventIdx in self.squatEvents['eventIdxs']:            
            coordValues = data[eventIdx[0]:eventIdx[1]]            
            coordValuesSegmentedNorm.append(np.stack([np.interp(np.linspace(0,100,101),
                                    np.linspace(0,100,len(coordValues)),coordValues[:,i]) \
                                    for i in range(coordValues.shape[1])],axis=1))
             
        coordValuesTimeNormalized = {}
        # Average.
        coordVals_mean = np.mean(np.array(coordValuesSegmentedNorm),axis=0)
        coordValuesTimeNormalized['mean'] = pd.DataFrame(data=coordVals_mean, columns=colNames)        
        # Standard deviation.
        if self.nRepetitions > 2:
            coordVals_sd = np.std(np.array(coordValuesSegmentedNorm), axis=0)
            coordValuesTimeNormalized['sd'] = pd.DataFrame(data=coordVals_sd, columns=colNames)
        else:
            coordValuesTimeNormalized['sd'] = None        
        # Indiv.
        coordValuesTimeNormalized['indiv'] = [pd.DataFrame(data=d, columns=colNames) for d in coordValuesSegmentedNorm]
        
        return coordValuesTimeNormalized
    
    def get_center_of_mass_segmented_normalized_time(self):
        
        data = np.vstack((self.comValues()['x'],self.comValues()['y'],self.comValues()['z'])).T        
        colNames = ['com_x', 'com_y', 'com_z']        
        comValuesSegmentedNorm = []
        for eventIdx in self.squatEvents['eventIdxs']:            
            comValues = data[eventIdx[0]:eventIdx[1]]            
            comValuesSegmentedNorm.append(np.stack([np.interp(np.linspace(0,100,101),
                                    np.linspace(0,100,len(comValues)),comValues[:,i]) \
                                    for i in range(comValues.shape[1])],axis=1))
             
        comValuesTimeNormalized = {}
        # Average.
        comValues_mean = np.mean(np.array(comValuesSegmentedNorm),axis=0)
        comValuesTimeNormalized['mean'] = pd.DataFrame(data=comValues_mean, columns=colNames)        
        # Standard deviation.
        if self.nRepetitions > 2:
            comValues_sd = np.std(np.array(comValuesSegmentedNorm), axis=0)
            comValuesTimeNormalized['sd'] = pd.DataFrame(data=comValues_sd, columns=colNames)
        else:
            comValuesTimeNormalized['sd'] = None        
        # Indiv.
        comValuesTimeNormalized['indiv'] = [pd.DataFrame(data=d, columns=colNames) for d in comValuesSegmentedNorm]
        
        return comValuesTimeNormalized 
