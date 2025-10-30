import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import Papa from 'papaparse';

interface ScheduleEntry {
  Date: string;
  Day: string;
  Weekend?: string;
  Chat?: string;
  OnCall?: string;
  Appointments?: string;
  Early?: string;
}

interface EngineerSchedule {
  engineer: string;
  entries: ScheduleEntry[];
  stats: {
    weekends: number;
    onCall: number;
    early: number;
    chat: number;
    appointments: number;
  };
}

const ScheduleViewer: React.FC = () => {
  const [scheduleData, setScheduleData] = useState<ScheduleEntry[]>([]);
  const [selectedEngineer, setSelectedEngineer] = useState<string>('all');
  const [viewMode, setViewMode] = useState<'calendar' | 'list' | 'stats'>('calendar');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (!file) return;

    if (!file.name.endsWith('.csv')) {
      setError('Please upload a CSV file');
      return;
    }

    setLoading(true);
    setError('');

    // Try server-side upload first for better analysis
    const formData = new FormData();
    formData.append('file', file);

    fetch('/api/upload-schedule', {
      method: 'POST',
      body: formData,
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        setScheduleData(data.schedule);
        setLoading(false);
      } else {
        throw new Error(data.error || 'Upload failed');
      }
    })
    .catch(() => {
      // Fallback to client-side parsing
      Papa.parse(file, {
        header: true,
        complete: (results) => {
          try {
            const data = results.data as ScheduleEntry[];
            // Filter out empty rows
            const validData = data.filter(row => row.Date && row.Day);
            setScheduleData(validData);
            setLoading(false);
          } catch (err) {
            setError('Error parsing CSV file');
            setLoading(false);
          }
        },
        error: (error) => {
          setError(`Error reading file: ${error.message}`);
          setLoading(false);
        }
      });
    });
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv']
    },
    multiple: false
  });

  // Get unique engineers from the schedule data
  const engineers = React.useMemo(() => {
    const engineerSet = new Set<string>();
    scheduleData.forEach(entry => {
      if (entry.Weekend) engineerSet.add(entry.Weekend);
      if (entry.Chat) engineerSet.add(entry.Chat);
      if (entry.OnCall) engineerSet.add(entry.OnCall);
      if (entry.Appointments) engineerSet.add(entry.Appointments);
      if (entry.Early) engineerSet.add(entry.Early);
    });
    return Array.from(engineerSet).sort();
  }, [scheduleData]);

  // Get engineer-specific schedule data
  const getEngineerSchedule = (engineer: string): EngineerSchedule => {
    const entries = scheduleData.filter(entry => 
      entry.Weekend === engineer ||
      entry.Chat === engineer ||
      entry.OnCall === engineer ||
      entry.Appointments === engineer ||
      entry.Early === engineer
    );

    const stats = {
      weekends: scheduleData.filter(entry => entry.Weekend === engineer).length,
      onCall: scheduleData.filter(entry => entry.OnCall === engineer).length,
      early: scheduleData.filter(entry => entry.Early === engineer).length,
      chat: scheduleData.filter(entry => entry.Chat === engineer).length,
      appointments: scheduleData.filter(entry => entry.Appointments === engineer).length,
    };

    return { engineer, entries, stats };
  };

  // Filter data based on selected engineer
  const filteredData = selectedEngineer === 'all' 
    ? scheduleData 
    : scheduleData.filter(entry => 
        entry.Weekend === selectedEngineer ||
        entry.Chat === selectedEngineer ||
        entry.OnCall === selectedEngineer ||
        entry.Appointments === selectedEngineer ||
        entry.Early === selectedEngineer
      );

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { 
      weekday: 'short', 
      month: 'short', 
      day: 'numeric' 
    });
  };

  const getRoleForEngineer = (entry: ScheduleEntry, engineer: string): string[] => {
    const roles: string[] = [];
    if (entry.Weekend === engineer) roles.push('Weekend');
    if (entry.Chat === engineer) roles.push('Chat');
    if (entry.OnCall === engineer) roles.push('OnCall');
    if (entry.Appointments === engineer) roles.push('Appointments');
    if (entry.Early === engineer) roles.push('Early');
    return roles;
  };

  const renderCalendarView = () => {
    if (selectedEngineer === 'all') {
      return (
        <div className="overflow-x-auto">
          <table className="min-w-full bg-white border border-gray-300">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 border-b text-left">Date</th>
                <th className="px-4 py-2 border-b text-left">Day</th>
                <th className="px-4 py-2 border-b text-left">Weekend</th>
                <th className="px-4 py-2 border-b text-left">Chat</th>
                <th className="px-4 py-2 border-b text-left">OnCall</th>
                <th className="px-4 py-2 border-b text-left">Appointments</th>
                <th className="px-4 py-2 border-b text-left">Early</th>
              </tr>
            </thead>
            <tbody>
              {filteredData.map((entry, index) => (
                <tr key={index} className={index % 2 === 0 ? 'bg-gray-50' : 'bg-white'}>
                  <td className="px-4 py-2 border-b">{formatDate(entry.Date)}</td>
                  <td className="px-4 py-2 border-b">{entry.Day}</td>
                  <td className="px-4 py-2 border-b">{entry.Weekend || '-'}</td>
                  <td className="px-4 py-2 border-b">{entry.Chat || '-'}</td>
                  <td className="px-4 py-2 border-b">{entry.OnCall || '-'}</td>
                  <td className="px-4 py-2 border-b">{entry.Appointments || '-'}</td>
                  <td className="px-4 py-2 border-b">{entry.Early || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    } else {
      return (
        <div className="space-y-4">
          {filteredData.map((entry, index) => {
            const roles = getRoleForEngineer(entry, selectedEngineer);
            if (roles.length === 0) return null;
            
            return (
              <div key={index} className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="font-semibold text-lg">{formatDate(entry.Date)}</h3>
                    <p className="text-gray-600">{entry.Day}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {roles.map(role => (
                      <span 
                        key={role}
                        className={`px-3 py-1 rounded-full text-sm font-medium ${
                          role === 'Weekend' ? 'bg-purple-100 text-purple-800' :
                          role === 'OnCall' ? 'bg-red-100 text-red-800' :
                          role === 'Early' ? 'bg-yellow-100 text-yellow-800' :
                          role === 'Chat' ? 'bg-blue-100 text-blue-800' :
                          'bg-green-100 text-green-800'
                        }`}
                      >
                        {role}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      );
    }
  };

  const renderStatsView = () => {
    const engineerStats = engineers.map(engineer => getEngineerSchedule(engineer));
    
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {engineerStats.map(({ engineer, stats }) => (
          <div key={engineer} className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm">
            <h3 className="font-semibold text-lg mb-4">{engineer}</h3>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span>Weekends:</span>
                <span className="font-medium">{stats.weekends}</span>
              </div>
              <div className="flex justify-between">
                <span>OnCall:</span>
                <span className="font-medium">{stats.onCall}</span>
              </div>
              <div className="flex justify-between">
                <span>Early Shifts:</span>
                <span className="font-medium">{stats.early}</span>
              </div>
              <div className="flex justify-between">
                <span>Chat:</span>
                <span className="font-medium">{stats.chat}</span>
              </div>
              <div className="flex justify-between">
                <span>Appointments:</span>
                <span className="font-medium">{stats.appointments}</span>
              </div>
              <div className="pt-2 border-t">
                <div className="flex justify-between font-semibold">
                  <span>Total:</span>
                  <span>{stats.weekends + stats.onCall + stats.early + stats.chat + stats.appointments}</span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-100 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Schedule Viewer</h1>
          <p className="text-gray-600">Upload a CSV schedule file to view and analyze engineer assignments</p>
        </div>

        {/* File Upload */}
        {scheduleData.length === 0 && (
          <div className="mb-8">
            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                isDragActive 
                  ? 'border-blue-400 bg-blue-50' 
                  : 'border-gray-300 hover:border-gray-400'
              }`}
            >
              <input {...getInputProps()} />
              <div className="space-y-4">
                <div className="text-4xl">📄</div>
                {loading ? (
                  <p className="text-gray-600">Processing file...</p>
                ) : isDragActive ? (
                  <p className="text-blue-600">Drop the CSV file here...</p>
                ) : (
                  <div>
                    <p className="text-gray-600 mb-2">Drag and drop a CSV schedule file here, or click to select</p>
                    <p className="text-sm text-gray-500">Supports CSV files exported from the scheduler</p>
                  </div>
                )}
              </div>
            </div>
            {error && (
              <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-red-600">{error}</p>
              </div>
            )}
          </div>
        )}

        {/* Controls */}
        {scheduleData.length > 0 && (
          <div className="mb-6 bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
            <div className="flex flex-wrap gap-4 items-center">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Engineer Filter
                </label>
                <select
                  value={selectedEngineer}
                  onChange={(e) => setSelectedEngineer(e.target.value)}
                  className="border border-gray-300 rounded-md px-3 py-2 bg-white"
                >
                  <option value="all">All Engineers</option>
                  {engineers.map(engineer => (
                    <option key={engineer} value={engineer}>{engineer}</option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  View Mode
                </label>
                <div className="flex border border-gray-300 rounded-md overflow-hidden">
                  <button
                    onClick={() => setViewMode('calendar')}
                    className={`px-4 py-2 text-sm font-medium ${
                      viewMode === 'calendar' 
                        ? 'bg-blue-500 text-white' 
                        : 'bg-white text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    Calendar
                  </button>
                  <button
                    onClick={() => setViewMode('stats')}
                    className={`px-4 py-2 text-sm font-medium border-l border-gray-300 ${
                      viewMode === 'stats' 
                        ? 'bg-blue-500 text-white' 
                        : 'bg-white text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    Statistics
                  </button>
                </div>
              </div>

              <div className="ml-auto">
                <button
                  onClick={() => {
                    setScheduleData([]);
                    setSelectedEngineer('all');
                    setViewMode('calendar');
                    setError('');
                  }}
                  className="px-4 py-2 bg-gray-500 text-white rounded-md hover:bg-gray-600 transition-colors"
                >
                  Upload New File
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Schedule Display */}
        {scheduleData.length > 0 && (
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
            <div className="mb-4">
              <h2 className="text-xl font-semibold">
                {viewMode === 'calendar' ? 'Schedule Calendar' : 'Assignment Statistics'}
                {selectedEngineer !== 'all' && ` - ${selectedEngineer}`}
              </h2>
              <p className="text-gray-600">
                Showing {filteredData.length} entries
                {selectedEngineer !== 'all' && ` for ${selectedEngineer}`}
              </p>
            </div>
            
            {viewMode === 'calendar' ? renderCalendarView() : renderStatsView()}
          </div>
        )}
      </div>
    </div>
  );
};

export default ScheduleViewer;