// Simple test to check date calculation logic
const startDate = "2025-11-09"; // Sunday
const weeks = 2;

const startDateObj = new Date(startDate);
console.log("Start date:", startDate, "Day of week:", startDateObj.getDay());

const includesPreviousSaturday = startDateObj.getDay() === 0;
console.log("Includes previous Saturday:", includesPreviousSaturday);

let actualStartDate;
let totalDays;

if (includesPreviousSaturday) {
  actualStartDate = new Date(startDateObj);
  actualStartDate.setDate(startDateObj.getDate() - 1);
  totalDays = (weeks * 7) + 1;
} else {
  actualStartDate = startDateObj;
  totalDays = weeks * 7;
}

console.log("Actual start date:", actualStartDate.toISOString().split('T')[0]);
console.log("Total days:", totalDays);

console.log("\nGenerated dates:");
for (let dayIndex = 0; dayIndex < totalDays; dayIndex++) {
  const currentDate = new Date(actualStartDate);
  currentDate.setDate(actualStartDate.getDate() + dayIndex);
  const dateStr = currentDate.toISOString().split('T')[0];
  const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  const dayName = dayNames[currentDate.getDay()];
  
  console.log(`Day ${dayIndex}: ${dateStr} (${dayName})`);
}