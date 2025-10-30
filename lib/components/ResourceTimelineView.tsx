import React, { useMemo } from 'react';

interface ScheduleEntry {
  Date: string;
  Day: string;
  Weekend?: string;
  Chat?: string;
  OnCall?: string;
  Appointments?: string;
  Early?: string;
}

interface ResourceTimelineViewProps {
  scheduleData: ScheduleEntry[];
  engineerColorMap: { [engineer: string]: any };
  selectedEngineer: string;
  onDayClick?: (entry: ScheduleEntry) => void;
}

const ROLE_COLORS = {
  Weekend: { bg: 'bg-purple-500', text: 'text-white', icon: '🏖️' },
  OnCall: { bg: 'bg-red-500', text: 'text-white', icon: '🚨' },
  Early: { bg: 'bg-yellow-500', text: 'text-white', icon: '🌅' },
  Chat: { bg: 'bg-blue-500', text: 'text-white', icon: '💬' },
  Appointments: { bg: 'bg-green-500', text: 'text-white', icon: '📅' },
};

const ResourceTimelineView: React.FC<ResourceTimelineViewProps> = ({
  scheduleData,
  engineerColorMap,
  selectedEngineer,
  onDayClick
}) => {
  // Get unique engineers and dates
  const { engineers, dateRange } = useMemo(() => {
    const engineerSet = new Set<string>();
    const dates = new Set<string>();
    
    scheduleData.forEach(entry => {
      dates.add(entry.Date);
      [entry.Weekend, entry.Chat, entry.OnCall, entry.Appointments, entry.Early]
        .filter(Boolean)
        .forEach(engineer => engineerSet.add(engineer!));
    });
    
    const sortedDates = Array.from(dates).sort();
    const engineerList = Array.from(engineerSet).sort();
    
    return {
      engineers: selectedEngineer === 'all' ? engineerList : [selectedEngineer],
      dateRange: sortedDates
    };
  }, [scheduleData, selectedEngineer]);

  // Create timeline data structure
  const timelineData = useMemo(() => {
    const data: { [engineer: string]: { [date: string]: string[] } } = {};
    
    engineers.forEach(engineer => {
      data[engineer] = {};
      dateRange.forEach(date => {
        data[engineer][date] = [];
      });
    });
    
    scheduleData.forEach(entry => {
      Object.entries({
        Weekend: entry.Weekend,
        OnCall: entry.OnCall,
        Early: entry.Early,
        Chat: entry.Chat,
        Appointments: entry.Appointments
      }).forEach(([role, engineer]) => {
        if (engineer && engineers.includes(engineer)) {
          if (!data[engineer][entry.Date]) {
            data[engineer][entry.Date] = [];
          }
          data[engineer][entry.Date].push(role);
        }
      });
    });
    
    return data;
  }, [scheduleData, engineers, dateRange]);

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return {
      day: date.toLocaleDateString('en-US', { weekday: 'short' }),
      date: date.getDate(),
      month: date.toLocaleDateString('en-US', { month: 'short' })
    };
  };

  const isToday = (dateStr: string) => {
    return new Date(dateStr).toDateString() === new Date().toDateString();
  };

  const isWeekend = (dateStr: string) => {
    const day = new Date(dateStr).getDay();
    return day === 0 || day === 6;
  };

  return (
    <div className="bg-white rounded-2xl shadow-xl border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-indigo-600 to-purple-600 p-6 text-white">
        <h3 className="text-2xl font-bold mb-2">👥 Resource Timeline</h3>
        <p className="text-indigo-100">
          {selectedEngineer === 'all' 
            ? `Showing ${engineers.length} engineers across ${dateRange.length} days`
            : `Individual timeline for ${selectedEngineer}`
          }
        </p>
      </div>

      {/* Timeline Container */}
      <div className="overflow-x-auto">
        <div className="min-w-full">
          {/* Date Headers */}
          <div className="sticky top-0 z-10 bg-gray-50 border-b border-gray-200">
            <div className="flex">
              {/* Engineer column header */}
              <div className="w-48 p-4 font-semibold text-gray-900 bg-gray-100 border-r border-gray-200">
                Engineer
              </div>
              
              {/* Date headers */}
              {dateRange.map(date => {
                const { day, date: dayNum, month } = formatDate(date);
                const today = isToday(date);
                const weekend = isWeekend(date);
                
                return (
                  <div 
                    key={date} 
                    className={`min-w-32 p-3 text-center border-r border-gray-200 ${
                      today 
                        ? 'bg-blue-500 text-white font-bold' 
                        : weekend 
                          ? 'bg-purple-100 text-purple-800'
                          : 'bg-gray-50 text-gray-700'
                    }`}
                  >
                    <div className="text-xs font-medium">{day}</div>
                    <div className="text-lg font-bold">{dayNum}</div>
                    <div className="text-xs opacity-75">{month}</div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Engineer Rows */}
          <div className="divide-y divide-gray-200">
            {engineers.map(engineer => {
              const colors = engineerColorMap[engineer] || { bg: 'bg-gray-100', text: 'text-gray-800', accent: 'bg-gray-500' };
              
              return (
                <div key={engineer} className="flex hover:bg-gray-50 transition-colors">
                  {/* Engineer Name */}
                  <div className={`w-48 p-4 border-r border-gray-200 ${colors.bg} ${colors.text} font-semibold flex items-center`}>
                    <div className={`w-3 h-3 rounded-full ${colors.accent} mr-3`}></div>
                    {engineer}
                  </div>
                  
                  {/* Timeline Cells */}
                  {dateRange.map(date => {
                    const roles = timelineData[engineer][date] || [];
                    const entry = scheduleData.find(e => e.Date === date);
                    const today = isToday(date);
                    const weekend = isWeekend(date);
                    
                    return (
                      <div 
                        key={`${engineer}-${date}`}
                        className={`min-w-32 p-2 border-r border-gray-200 cursor-pointer hover:bg-blue-50 transition-colors ${
                          today ? 'bg-blue-50' : weekend ? 'bg-purple-25' : ''
                        }`}
                        onClick={() => entry && onDayClick?.(entry)}
                      >
                        <div className="space-y-1">
                          {roles.length > 0 ? (
                            roles.map((role, index) => {
                              const roleConfig = ROLE_COLORS[role as keyof typeof ROLE_COLORS];
                              return (
                                <div 
                                  key={index}
                                  className={`px-2 py-1 rounded text-xs font-medium ${roleConfig.bg} ${roleConfig.text} flex items-center justify-center gap-1`}
                                >
                                  <span>{roleConfig.icon}</span>
                                  <span className="truncate">{role}</span>
                                </div>
                              );
                            })
                          ) : (
                            <div className="h-6 flex items-center justify-center text-gray-400 text-xs">
                              -
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className="bg-gray-50 p-4 border-t border-gray-200">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-semibold text-gray-700">Role Legend</h4>
          <div className="text-xs text-gray-500">Click any cell for details</div>
        </div>
        <div className="flex flex-wrap gap-3 mt-2">
          {Object.entries(ROLE_COLORS).map(([role, config]) => (
            <div key={role} className={`flex items-center gap-2 px-2 py-1 rounded ${config.bg} ${config.text}`}>
              <span>{config.icon}</span>
              <span className="text-xs font-medium">{role}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ResourceTimelineView;