// Debug the weekend week calculation logic
const startDate = "2025-01-05"; // Sunday start
const startDateObj = new Date(startDate);
const engineers = ["Engineer A", "Engineer B", "Engineer C", "Engineer D", "Engineer E", "Engineer F"];
const seeds = { weekend: 0 };

console.log("Start date:", startDate, "Day of week:", startDateObj.getDay());
console.log("Engineers:", engineers);
console.log("Seeds.weekend:", seeds.weekend);

// Test first 10 weekends
for (let week = 0; week < 10; week++) {
  // Saturday
  const saturdayDate = new Date(startDateObj);
  saturdayDate.setDate(startDateObj.getDate() + (week * 7) - 1); // Saturday before Sunday
  
  // Sunday  
  const sundayDate = new Date(startDateObj);
  sundayDate.setDate(startDateObj.getDate() + (week * 7)); // Sunday
  
  console.log(`\nWeek ${week}:`);
  console.log(`  Saturday: ${saturdayDate.toISOString().split('T')[0]} (day ${saturdayDate.getDay()})`);
  console.log(`  Sunday: ${sundayDate.toISOString().split('T')[0]} (day ${sundayDate.getDay()})`);
  
  // Calculate weekendWeek for Saturday (using the logic from the API)
  const nextDay = new Date(saturdayDate);
  nextDay.setDate(saturdayDate.getDate() + 1);
  const daysSinceSundayStart = Math.floor((nextDay.getTime() - startDateObj.getTime()) / (24 * 60 * 60 * 1000));
  const saturdayWeekendWeek = Math.floor(daysSinceSundayStart / 7);
  
  // Calculate weekendWeek for Sunday
  const sundayDaysSinceStart = Math.floor((sundayDate.getTime() - startDateObj.getTime()) / (24 * 60 * 60 * 1000));
  const sundayWeekendWeek = Math.floor(sundayDaysSinceStart / 7);
  
  console.log(`  Saturday weekendWeek: ${saturdayWeekendWeek}`);
  console.log(`  Sunday weekendWeek: ${sundayWeekendWeek}`);
  
  // Calculate which engineer should be assigned
  const saturdayEngineerIdx = (saturdayWeekendWeek + seeds.weekend) % engineers.length;
  const sundayEngineerIdx = (sundayWeekendWeek + seeds.weekend) % engineers.length;
  
  console.log(`  Saturday engineer: ${engineers[saturdayEngineerIdx]} (idx ${saturdayEngineerIdx})`);
  console.log(`  Sunday engineer: ${engineers[sundayEngineerIdx]} (idx ${sundayEngineerIdx})`);
}