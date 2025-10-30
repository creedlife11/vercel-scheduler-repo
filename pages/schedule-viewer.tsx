import React, { useState, useCallback, useMemo } from 'react';
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
    total: number;
  };
}

// Engineer color palette - consistent colors for each engineer
const ENGINEER_COLORS = [
  { bg: 'bg-blue-100', text: 'text-blue-800', border: 'border-blue-200', accent: 'bg-blue-500' },
  { bg: 'bg-green-100', text: 'text-green-800', border: 'border-green-200', accent: 'bg-green-500' },
  { bg: 'bg-purple-100', text: 'text-purple-800', border: 'border-purple-200', accent: 'bg-purple-500' },
  { bg: 'bg-orange-100', text: 'text-orange-800', border: 'border-orange-200', accent: 'bg-orange-500' },
  { bg: 'bg-pink-100', text: 'text-pink-800', border: 'border-pink-200', accent: 'bg-pink-500' },
  { bg: 'bg-indigo-100', text: 'text-indigo-800', border: 'border-indigo-200', accent: 'bg-indigo-500' },
  { bg: 'bg-teal-100', text: 'text-teal-800', border: 'border-teal-200', accent: 'bg-teal-500' },
  { bg: 'bg-red-100', text: 'text-red-800', border: 'border-red-200', accent: 'bg-red-500' },
];

const ROLE_COLORS = {
  Weekend: { bg: 'bg-purple-100', text: 'text-purple-800', icon: '🏖️' },
  OnCall: { bg: 'bg-red-100', text: 'text-red-800', icon: '🚨' },
  Early: { bg: 'bg-yellow-100', text: 'text-yellow-800', icon: '🌅' },
  Chat: { bg: 'bg-blue-100', text: 'text-blue-800', icon: '💬' },
  Appointments: { bg: 'bg-green-100', text: 'text-green-800', icon: '📅' },
};

const ScheduleViewer: React.FC = () => {
  const [scheduleData, setScheduleData] = useState<ScheduleEntry[]>([]);
  const [selectedEngineer, setSelectedEngineer] = useState<string>('all');
  const [viewMode, setViewMode] = useState<'calendar' | 'dashboard' | 'stats'>('dashboard');
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
  const engineers = useMemo(() => {
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

  // Create engineer color mapping
  const engineerColorMap = useMemo(() => {
    const colorMap: { [engineer: string]: typeof ENGINEER_COLORS[0] } = {};
    engineers.forEach((engineer, index) => {
      colorMap[engineer] = ENGINEER_COLORS[index % ENGINEER_COLORS.length];
    });
    return colorMap;
  }, [engineers]);

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
      total: 0
    };
    
    stats.total = stats.weekends + stats.onCall + stats.early + stats.chat + stats.appointments;

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

  const formatDateLong = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { 
      weekday: 'long', 
      year: 'numeric',
      month: 'long', 
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

  const getEngineerBadge = (engineer: string, size: 'sm' | 'md' | 'lg' = 'md') => {
    const colors = engineerColorMap[engineer] || ENGINEER_COLORS[0];
    const sizeClasses = {
      sm: 'px-2 py-1 text-xs',
      md: 'px-3 py-1 text-sm',
      lg: 'px-4 py-2 text-base'
    };
    
    return (
      <span className={`inline-flex items-center ${sizeClasses[size]} font-medium rounded-full ${colors.bg} ${colors.text} ${colors.border} border`}>
        {engineer}
      </span>
    );
  };

  const getRoleBadge = (role: string, size: 'sm' | 'md' = 'sm') => {
    const roleConfig = ROLE_COLORS[role as keyof typeof ROLE_COLORS];
    if (!roleConfig) return null;
    
    const sizeClasses = size === 'sm' ? 'px-2 py-1 text-xs' : 'px-3 py-1 text-sm';
    
    return (
      <span className={`inline-flex items-center gap-1 ${sizeClasses} font-medium rounded-full ${roleConfig.bg} ${roleConfig.text}`}>
        <span>{roleConfig.icon}</span>
        {role}
      </span>
    );
  };

  const renderDashboardView = () => {
    if (selectedEngineer === 'all') {
      // Overview dashboard for all engineers
      const totalEntries = scheduleData.length;

      return (
        <div className="space-y-6">
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-gradient-to-r from-blue-500 to-blue-600 p-6 rounded-xl text-white shadow-lg">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-blue-100 text-sm font-medium">Total Days</p>
                  <p className="text-3xl font-bold">{totalEntries}</p>
                </div>
                <div className="text-4xl opacity-80">📅</div>
              </div>
            </div>
            
            <div className="bg-gradient-to-r from-green-500 to-green-600 p-6 rounded-xl text-white shadow-lg">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-green-100 text-sm font-medium">Engineers</p>
                  <p className="text-3xl font-bold">{engineers.length}</p>
                </div>
                <div className="text-4xl opacity-80">👥</div>
              </div>
            </div>
            
            <div className="bg-gradient-to-r from-purple-500 to-purple-600 p-6 rounded-xl text-white shadow-lg">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-purple-100 text-sm font-medium">Weekends</p>
                  <p className="text-3xl font-bold">{scheduleData.filter(e => e.Weekend).length}</p>
                </div>
                <div className="text-4xl opacity-80">🏖️</div>
              </div>
            </div>
            
            <div className="bg-gradient-to-r from-red-500 to-red-600 p-6 rounded-xl text-white shadow-lg">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-red-100 text-sm font-medium">OnCall Days</p>
                  <p className="text-3xl font-bold">{scheduleData.filter(e => e.OnCall).length}</p>
                </div>
                <div className="text-4xl opacity-80">🚨</div>
              </div>
            </div>
          </div>

          {/* Engineer Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {engineers.map(engineer => {
              const engineerSchedule = getEngineerSchedule(engineer);
              const colors = engineerColorMap[engineer];
              
              return (
                <div key={engineer} className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden hover:shadow-xl transition-shadow duration-300">
                  <div className={`${colors.accent} p-4`}>
                    <div className="flex items-center justify-between text-white">
                      <h3 className="text-lg font-semibold">{engineer}</h3>
                      <div className="text-2xl opacity-80">👤</div>
                    </div>
                  </div>
                  
                  <div className="p-6">
                    <div className="grid grid-cols-2 gap-4 mb-4">
                      <div className="text-center">
                        <div className="text-2xl font-bold text-gray-900">{engineerSchedule.stats.total}</div>
                        <div className="text-sm text-gray-500">Total Assignments</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-purple-600">{engineerSchedule.stats.weekends}</div>
                        <div className="text-sm text-gray-500">Weekends</div>
                      </div>
                    </div>
                    
                    <div className="space-y-2">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">🚨 OnCall</span>
                        <span className="font-medium">{engineerSchedule.stats.onCall}</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">🌅 Early</span>
                        <span className="font-medium">{engineerSchedule.stats.early}</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">💬 Chat</span>
                        <span className="font-medium">{engineerSchedule.stats.chat}</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">📅 Appointments</span>
                        <span className="font-medium">{engineerSchedule.stats.appointments}</span>
                      </div>
                    </div>
                    
                    <button
                      onClick={() => setSelectedEngineer(engineer)}
                      className={`mt-4 w-full ${colors.accent} text-white py-2 px-4 rounded-lg hover:opacity-90 transition-opacity duration-200 font-medium`}
                    >
                      View Details
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      );
    } else {
      // Individual engineer dashboard
      const engineerSchedule = getEngineerSchedule(selectedEngineer);
      const colors = engineerColorMap[selectedEngineer];
      
      return (
        <div className="space-y-6">
          {/* Engineer Header */}
          <div className={`${colors.accent} rounded-xl p-6 text-white shadow-lg`}>
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold">{selectedEngineer}</h2>
                <p className="text-white/80">Schedule Overview</p>
              </div>
              <div className="text-right">
                <div className="text-3xl font-bold">{engineerSchedule.stats.total}</div>
                <div className="text-white/80">Total Assignments</div>
              </div>
            </div>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {Object.entries(ROLE_COLORS).map(([role, config]) => {
              const count = engineerSchedule.stats[role.toLowerCase() as keyof typeof engineerSchedule.stats] || 0;
              return (
                <div key={role} className={`${config.bg} p-4 rounded-lg border ${config.text}`}>
                  <div className="text-center">
                    <div className="text-2xl mb-1">{config.icon}</div>
                    <div className="text-2xl font-bold">{count}</div>
                    <div className="text-sm font-medium">{role}</div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Timeline */}
          <div className="bg-white rounded-xl shadow-lg border border-gray-200 p-6">
            <h3 className="text-lg font-semibold mb-4">Assignment Timeline</h3>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {engineerSchedule.entries.map((entry, index) => {
                const roles = getRoleForEngineer(entry, selectedEngineer);
                return (
                  <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors duration-200">
                    <div>
                      <div className="font-medium text-gray-900">{formatDateLong(entry.Date)}</div>
                      <div className="text-sm text-gray-500">{entry.Day}</div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {roles.map(role => getRoleBadge(role))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      );
    }
  };

  const renderCalendarView = () => {
    if (selectedEngineer === 'all') {
      return (
        <div className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead className="bg-gradient-to-r from-gray-50 to-gray-100">
                <tr>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Day</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">🏖️ Weekend</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">💬 Chat</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">🚨 OnCall</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">📅 Appointments</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">🌅 Early</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredData.map((entry, index) => {
                  const isWeekend = entry.Day === 'Saturday' || entry.Day === 'Sunday';
                  return (
                    <tr key={index} className={`hover:bg-gray-50 transition-colors duration-200 ${isWeekend ? 'bg-purple-50' : ''}`}>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">{formatDate(entry.Date)}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                          isWeekend ? 'bg-purple-100 text-purple-800' : 'bg-gray-100 text-gray-800'
                        }`}>
                          {entry.Day}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {entry.Weekend ? getEngineerBadge(entry.Weekend, 'sm') : <span className="text-gray-400">-</span>}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {entry.Chat ? getEngineerBadge(entry.Chat, 'sm') : <span className="text-gray-400">-</span>}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {entry.OnCall ? getEngineerBadge(entry.OnCall, 'sm') : <span className="text-gray-400">-</span>}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {entry.Appointments ? getEngineerBadge(entry.Appointments, 'sm') : <span className="text-gray-400">-</span>}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {entry.Early ? getEngineerBadge(entry.Early, 'sm') : <span className="text-gray-400">-</span>}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      );
    } else {
      return (
        <div className="space-y-4">
          {filteredData.map((entry, index) => {
            const roles = getRoleForEngineer(entry, selectedEngineer);
            if (roles.length === 0) return null;
            
            const isWeekend = entry.Day === 'Saturday' || entry.Day === 'Sunday';
            const colors = engineerColorMap[selectedEngineer];
            
            return (
              <div key={index} className={`bg-white p-6 rounded-xl border-2 shadow-lg hover:shadow-xl transition-all duration-300 ${colors.border} ${isWeekend ? 'ring-2 ring-purple-200' : ''}`}>
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="font-bold text-xl text-gray-900">{formatDate(entry.Date)}</h3>
                      <span className={`px-3 py-1 text-sm font-semibold rounded-full ${
                        isWeekend ? 'bg-purple-100 text-purple-800' : 'bg-gray-100 text-gray-800'
                      }`}>
                        {entry.Day}
                      </span>
                    </div>
                    <p className="text-gray-600 mb-3">{formatDateLong(entry.Date)}</p>
                    <div className="flex flex-wrap gap-2">
                      {roles.map(role => getRoleBadge(role, 'md'))}
                    </div>
                  </div>
                  <div className={`w-4 h-full ${colors.accent} rounded-full opacity-20`}></div>
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
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-blue-50 to-indigo-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8 text-center">
          <div className="inline-flex items-center gap-3 mb-4">
            <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl flex items-center justify-center text-white text-2xl shadow-lg">
              📊
            </div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent">
              Schedule Viewer
            </h1>
          </div>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Upload a CSV schedule file to view and analyze engineer assignments with rich visual analytics
          </p>
        </div>

        {/* File Upload */}
        {scheduleData.length === 0 && (
          <div className="mb-8 max-w-2xl mx-auto">
            <div
              {...getRootProps()}
              className={`relative border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all duration-300 ${
                isDragActive 
                  ? 'border-blue-400 bg-blue-50 scale-105 shadow-lg' 
                  : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50 hover:shadow-md'
              }`}
            >
              <input {...getInputProps()} />
              <div className="space-y-6">
                <div className={`text-6xl transition-transform duration-300 ${isDragActive ? 'scale-110' : ''}`}>
                  {loading ? '⏳' : isDragActive ? '📥' : '📄'}
                </div>
                {loading ? (
                  <div className="space-y-2">
                    <p className="text-lg font-medium text-gray-700">Processing file...</p>
                    <div className="w-32 h-2 bg-gray-200 rounded-full mx-auto overflow-hidden">
                      <div className="h-full bg-gradient-to-r from-blue-500 to-purple-600 rounded-full animate-pulse"></div>
                    </div>
                  </div>
                ) : isDragActive ? (
                  <div className="space-y-2">
                    <p className="text-xl font-semibold text-blue-600">Drop the CSV file here!</p>
                    <p className="text-blue-500">Release to upload your schedule</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div>
                      <p className="text-xl font-semibold text-gray-700 mb-2">Upload Your Schedule</p>
                      <p className="text-gray-600 mb-1">Drag and drop a CSV schedule file here, or click to browse</p>
                      <p className="text-sm text-gray-500">Supports CSV files exported from the scheduler</p>
                    </div>
                    <div className="flex items-center justify-center gap-4 text-sm text-gray-500">
                      <span className="flex items-center gap-1">
                        <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                        Drag & Drop
                      </span>
                      <span className="flex items-center gap-1">
                        <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
                        Click to Browse
                      </span>
                      <span className="flex items-center gap-1">
                        <span className="w-2 h-2 bg-purple-500 rounded-full"></span>
                        Auto Analysis
                      </span>
                    </div>
                  </div>
                )}
              </div>
              
              {/* Decorative elements */}
              <div className="absolute top-4 left-4 w-8 h-8 border-2 border-gray-200 rounded-full opacity-20"></div>
              <div className="absolute top-4 right-4 w-6 h-6 border-2 border-gray-200 rounded-full opacity-20"></div>
              <div className="absolute bottom-4 left-6 w-4 h-4 border-2 border-gray-200 rounded-full opacity-20"></div>
              <div className="absolute bottom-4 right-8 w-10 h-10 border-2 border-gray-200 rounded-full opacity-20"></div>
            </div>
            
            {error && (
              <div className="mt-6 p-4 bg-red-50 border-l-4 border-red-400 rounded-lg shadow-sm">
                <div className="flex items-center">
                  <div className="text-red-400 text-xl mr-3">⚠️</div>
                  <p className="text-red-700 font-medium">{error}</p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Controls */}
        {scheduleData.length > 0 && (
          <div className="mb-8">
            <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6">
              <div className="flex flex-wrap gap-6 items-end">
                <div className="flex-1 min-w-48">
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    👤 Engineer Filter
                  </label>
                  <select
                    value={selectedEngineer}
                    onChange={(e) => setSelectedEngineer(e.target.value)}
                    className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all duration-200"
                  >
                    <option value="all">🌟 All Engineers</option>
                    {engineers.map(engineer => (
                      <option key={engineer} value={engineer}>👤 {engineer}</option>
                    ))}
                  </select>
                </div>
                
                <div className="flex-1 min-w-64">
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    📊 View Mode
                  </label>
                  <div className="flex bg-gray-100 rounded-xl p-1">
                    <button
                      onClick={() => setViewMode('dashboard')}
                      className={`flex-1 px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200 ${
                        viewMode === 'dashboard' 
                          ? 'bg-white text-blue-600 shadow-md' 
                          : 'text-gray-600 hover:text-gray-900'
                      }`}
                    >
                      📈 Dashboard
                    </button>
                    <button
                      onClick={() => setViewMode('calendar')}
                      className={`flex-1 px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200 ${
                        viewMode === 'calendar' 
                          ? 'bg-white text-blue-600 shadow-md' 
                          : 'text-gray-600 hover:text-gray-900'
                      }`}
                    >
                      📅 Calendar
                    </button>
                    <button
                      onClick={() => setViewMode('stats')}
                      className={`flex-1 px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200 ${
                        viewMode === 'stats' 
                          ? 'bg-white text-blue-600 shadow-md' 
                          : 'text-gray-600 hover:text-gray-900'
                      }`}
                    >
                      📊 Statistics
                    </button>
                  </div>
                </div>

                <div>
                  <button
                    onClick={() => {
                      setScheduleData([]);
                      setSelectedEngineer('all');
                      setViewMode('dashboard');
                      setError('');
                    }}
                    className="px-6 py-3 bg-gradient-to-r from-gray-500 to-gray-600 text-white rounded-xl hover:from-gray-600 hover:to-gray-700 transition-all duration-200 font-medium shadow-lg hover:shadow-xl"
                  >
                    🔄 Upload New File
                  </button>
                </div>
              </div>
              
              {/* Quick Stats Bar */}
              <div className="mt-6 pt-6 border-t border-gray-200">
                <div className="flex flex-wrap gap-6 text-sm">
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 bg-blue-500 rounded-full"></span>
                    <span className="text-gray-600">
                      <span className="font-semibold text-gray-900">{filteredData.length}</span> entries
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 bg-green-500 rounded-full"></span>
                    <span className="text-gray-600">
                      <span className="font-semibold text-gray-900">{engineers.length}</span> engineers
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 bg-purple-500 rounded-full"></span>
                    <span className="text-gray-600">
                      <span className="font-semibold text-gray-900">{scheduleData.filter(e => e.Weekend).length}</span> weekend days
                    </span>
                  </div>
                  {selectedEngineer !== 'all' && (
                    <div className="flex items-center gap-2">
                      <span className={`w-3 h-3 rounded-full ${engineerColorMap[selectedEngineer]?.accent || 'bg-gray-500'}`}></span>
                      <span className="text-gray-600">
                        Viewing <span className="font-semibold text-gray-900">{selectedEngineer}</span>
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Schedule Display */}
        {scheduleData.length > 0 && (
          <div>
            {viewMode === 'dashboard' && renderDashboardView()}
            {viewMode === 'calendar' && (
              <div>
                <div className="mb-6">
                  <h2 className="text-2xl font-bold text-gray-900 mb-2">
                    📅 Schedule Calendar
                    {selectedEngineer !== 'all' && ` - ${selectedEngineer}`}
                  </h2>
                  <p className="text-gray-600">
                    {selectedEngineer === 'all' 
                      ? `Complete schedule overview with ${filteredData.length} entries`
                      : `Individual schedule for ${selectedEngineer} with ${filteredData.length} assignments`
                    }
                  </p>
                </div>
                {renderCalendarView()}
              </div>
            )}
            {viewMode === 'stats' && (
              <div>
                <div className="mb-6">
                  <h2 className="text-2xl font-bold text-gray-900 mb-2">
                    📊 Assignment Statistics
                  </h2>
                  <p className="text-gray-600">
                    Detailed breakdown of role assignments across all engineers
                  </p>
                </div>
                {renderStatsView()}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ScheduleViewer;