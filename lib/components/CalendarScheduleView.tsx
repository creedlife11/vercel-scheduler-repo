import React, { useMemo, useState } from 'react';
import { Calendar, momentLocalizer, View, Views } from 'react-big-calendar';
import moment from 'moment';
import 'react-big-calendar/lib/css/react-big-calendar.css';

const localizer = momentLocalizer(moment);

interface ScheduleEntry {
  Date: string;
  Day: string;
  Weekend?: string;
  Chat?: string;
  OnCall?: string;
  Appointments?: string;
  Early?: string;
}

interface CalendarEvent {
  id: string;
  title: string;
  start: Date;
  end: Date;
  resource: string;
  engineer: string;
  role: string;
  allDay?: boolean;
  color: string;
}

interface CalendarScheduleViewProps {
  scheduleData: ScheduleEntry[];
  engineerColorMap: { [engineer: string]: any };
  selectedEngineer: string;
  onEventClick?: (event: CalendarEvent) => void;
}

const ROLE_COLORS = {
  Weekend: '#8b5cf6', // purple
  OnCall: '#ef4444',  // red
  Early: '#f59e0b',   // amber
  Chat: '#3b82f6',    // blue
  Appointments: '#10b981', // emerald
};

const CalendarScheduleView: React.FC<CalendarScheduleViewProps> = ({
  scheduleData,
  engineerColorMap,
  selectedEngineer,
  onEventClick
}) => {
  const [currentView, setCurrentView] = useState<View>(Views.WEEK);
  const [currentDate, setCurrentDate] = useState(new Date());

  // Transform schedule data into calendar events
  const calendarEvents = useMemo(() => {
    const events: CalendarEvent[] = [];
    
    scheduleData.forEach((entry, index) => {
      const date = new Date(entry.Date);
      
      // Create events for each role assignment
      Object.entries({
        Weekend: entry.Weekend,
        OnCall: entry.OnCall,
        Early: entry.Early,
        Chat: entry.Chat,
        Appointments: entry.Appointments
      }).forEach(([role, engineer]) => {
        if (engineer && (selectedEngineer === 'all' || engineer === selectedEngineer)) {
          // Set appropriate times for different roles
          let startHour = 9;
          let duration = 8; // hours
          
          switch (role) {
            case 'Weekend':
              startHour = 0;
              duration = 24;
              break;
            case 'OnCall':
              startHour = 0;
              duration = 24;
              break;
            case 'Early':
              startHour = 6;
              duration = 8;
              break;
            case 'Chat':
              startHour = 9;
              duration = 8;
              break;
            case 'Appointments':
              startHour = 10;
              duration = 6;
              break;
          }
          
          const start = new Date(date);
          start.setHours(startHour, 0, 0, 0);
          
          const end = new Date(start);
          end.setHours(startHour + duration, 0, 0, 0);
          
          events.push({
            id: `${index}-${role}-${engineer}`,
            title: `${role}: ${engineer}`,
            start,
            end,
            resource: engineer,
            engineer,
            role,
            allDay: role === 'Weekend',
            color: ROLE_COLORS[role as keyof typeof ROLE_COLORS] || '#6b7280'
          });
        }
      });
    });
    
    return events;
  }, [scheduleData, selectedEngineer]);

  // Get unique engineers for resource view (for future use)
  // const engineers = useMemo(() => {
  //   const engineerSet = new Set<string>();
  //   scheduleData.forEach(entry => {
  //     [entry.Weekend, entry.Chat, entry.OnCall, entry.Appointments, entry.Early]
  //       .filter(Boolean)
  //       .forEach(engineer => engineerSet.add(engineer!));
  //   });
  //   return Array.from(engineerSet).sort();
  // }, [scheduleData]);

  // Custom event component
  const EventComponent = ({ event }: { event: CalendarEvent }) => {
    // const colors = engineerColorMap[event.engineer] || { bg: 'bg-gray-100', text: 'text-gray-800' };
    
    return (
      <div 
        className={`h-full w-full rounded px-2 py-1 text-xs font-medium cursor-pointer hover:opacity-80 transition-opacity`}
        style={{ 
          backgroundColor: event.color,
          color: 'white',
          border: `2px solid ${event.color}`,
          borderRadius: '6px'
        }}
        onClick={() => onEventClick?.(event)}
      >
        <div className="font-semibold truncate">{event.engineer}</div>
        <div className="text-xs opacity-90 truncate">{event.role}</div>
      </div>
    );
  };

  // Custom toolbar
  const CustomToolbar = ({ onNavigate, onView }: any) => (
    <div className="flex items-center justify-between mb-6 p-4 bg-white rounded-xl shadow-lg border border-gray-200">
      <div className="flex items-center gap-4">
        <button
          onClick={() => onNavigate('PREV')}
          className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors font-medium"
        >
          ← Previous
        </button>
        <button
          onClick={() => onNavigate('TODAY')}
          className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors font-medium"
        >
          Today
        </button>
        <button
          onClick={() => onNavigate('NEXT')}
          className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors font-medium"
        >
          Next →
        </button>
      </div>
      
      <h2 className="text-xl font-bold text-gray-900">{moment(currentDate).format('MMMM YYYY')}</h2>
      
      <div className="flex items-center gap-2">
        {[
          { view: Views.DAY, label: 'Day' },
          { view: Views.WEEK, label: 'Week' },
          { view: Views.MONTH, label: 'Month' }
        ].map(({ view, label }) => (
          <button
            key={view}
            onClick={() => onView(view)}
            className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              currentView === view
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
            }`}
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  );

  // Custom day header
  const CustomHeader = ({ date, label }: any) => {
    const isToday = moment(date).isSame(moment(), 'day');
    const isWeekend = moment(date).day() === 0 || moment(date).day() === 6;
    
    return (
      <div className={`text-center p-3 font-semibold ${
        isToday 
          ? 'bg-blue-500 text-white rounded-lg' 
          : isWeekend 
            ? 'bg-purple-100 text-purple-800 rounded-lg'
            : 'text-gray-700'
      }`}>
        <div className="text-sm">{moment(date).format('ddd')}</div>
        <div className={`text-lg ${isToday ? 'font-bold' : ''}`}>
          {moment(date).format('D')}
        </div>
      </div>
    );
  };

  return (
    <div className="h-full">
      <style jsx global>{`
        .rbc-calendar {
          height: calc(100vh - 200px);
          font-family: 'Inter', system-ui, sans-serif;
        }
        
        .rbc-header {
          padding: 0;
          border: none;
          background: transparent;
        }
        
        .rbc-time-view .rbc-time-gutter,
        .rbc-time-view .rbc-time-content {
          border-color: #e5e7eb;
        }
        
        .rbc-time-slot {
          border-color: #f3f4f6;
        }
        
        .rbc-timeslot-group {
          border-color: #e5e7eb;
        }
        
        .rbc-day-slot .rbc-time-slot {
          border-top: 1px solid #f3f4f6;
        }
        
        .rbc-time-header-content {
          border-left: 1px solid #e5e7eb;
        }
        
        .rbc-today {
          background-color: #eff6ff;
        }
        
        .rbc-off-range-bg {
          background-color: #f9fafb;
        }
        
        .rbc-event {
          border: none;
          border-radius: 6px;
          padding: 2px 6px;
          font-size: 12px;
          font-weight: 500;
        }
        
        .rbc-event:hover {
          opacity: 0.8;
        }
        
        .rbc-event-allday {
          border-radius: 6px;
          padding: 4px 8px;
        }
        
        .rbc-month-view {
          border: 1px solid #e5e7eb;
          border-radius: 12px;
          overflow: hidden;
        }
        
        .rbc-month-row {
          border-color: #e5e7eb;
        }
        
        .rbc-date-cell {
          padding: 8px;
        }
        
        .rbc-date-cell > a {
          color: #374151;
          font-weight: 600;
        }
        
        .rbc-date-cell.rbc-off-range > a {
          color: #9ca3af;
        }
        
        .rbc-show-more {
          background-color: #f3f4f6;
          color: #6b7280;
          border-radius: 4px;
          padding: 2px 6px;
          font-size: 11px;
          font-weight: 500;
        }
        
        .rbc-toolbar {
          display: none; /* We use custom toolbar */
        }
      `}</style>
      
      <CustomToolbar
        onNavigate={(action: string) => {
          const newDate = new Date(currentDate);
          if (action === 'PREV') {
            if (currentView === Views.MONTH) {
              newDate.setMonth(newDate.getMonth() - 1);
            } else {
              newDate.setDate(newDate.getDate() - 7);
            }
          } else if (action === 'NEXT') {
            if (currentView === Views.MONTH) {
              newDate.setMonth(newDate.getMonth() + 1);
            } else {
              newDate.setDate(newDate.getDate() + 7);
            }
          } else if (action === 'TODAY') {
            setCurrentDate(new Date());
            return;
          }
          setCurrentDate(newDate);
        }}
        onView={(view: View) => setCurrentView(view)}
      />
      
      <div className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
        <Calendar
          localizer={localizer}
          events={calendarEvents}
          startAccessor="start"
          endAccessor="end"
          view={currentView}
          onView={setCurrentView}
          date={currentDate}
          onNavigate={setCurrentDate}
          components={{
            event: EventComponent,
            month: {
              header: CustomHeader
            },
            week: {
              header: CustomHeader
            },
            day: {
              header: CustomHeader
            }
          }}
          eventPropGetter={(event: CalendarEvent) => ({
            style: {
              backgroundColor: event.color,
              borderColor: event.color,
              color: 'white'
            }
          })}
          onSelectEvent={(event: CalendarEvent) => onEventClick?.(event)}
          popup
          showMultiDayTimes
          step={60}
          timeslots={1}
          min={new Date(2024, 0, 1, 6, 0)} // 6 AM
          max={new Date(2024, 0, 1, 22, 0)} // 10 PM
        />
      </div>
    </div>
  );
};

export default CalendarScheduleView;