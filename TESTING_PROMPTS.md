<h1> create_todo - Test Prompts</h1>

  1. All fields included:
  "Create a high priority todo to finish the quarterly report by Friday with a description that includes executive summary and financial analysis"
  2. Title + Priority:
  "Add a low priority task to organize my desk"
  3. Title + Description:
  "I need to schedule a dentist appointment, make sure to call them between 9-5 PM on weekdays"
  4. Title + Status:
  "Add a completed todo for yesterday's code review"
  5. Title only (minimal):
  "Remind me to buy groceries"

  list_todos - Test Prompts (Done)

  1. All active todos:
  "Show me all my active tasks" (Working)
  2. Filter by status:
  "What todos have I completed?" (Working)
  3. Filter by priority:
  "List all high priority tasks" ==> (Working now)
  4. Combined filters:
  "Show me active todos that are medium or high priority" (Working)
  5. General list:
  "What's on my todo list?" (Working)

  update_todo - Test Prompts (Done All Working)

  1. Update status:
  "Mark the grocery shopping task as completed"
  2. Update priority:
  "Change the quarterly report to high priority" (success message but not updating in database)
  3. Update title and description:
  "Update the dentist appointment to include scheduling a cleaning, and rename it to 'Dentist appointment + cleaning'"
  4. Multiple field update:
  "Set the desk organization task to medium priority and mark it as active" (success message but not updating in database)
  5. Simple status change:
  "I finished the code review task"

  delete_todo - Test Prompts

  1. Delete by title:
  "Delete the task about organizing my desk"
  2. Delete completed:
  "Remove all completed todos"
  3. Delete specific:
  "Delete todo number 5" or "Remove the grocery shopping task"
  4. Conversational delete:
  "I don't need to do the quarterly report anymore, remove it"
  5. Delete by status:
  "Clear out all my archived tasks"

  search_todos - Bonus Test Prompts

  1. Keyword search:
  "Find todos related to reports"
  2. Search in description:
  "Search for tasks that mention 'meeting' in the description"
  3. Date-based search:
  "Show me todos created this week"
  4. Combined search:
  "Find high priority active tasks about the project"
  5. Fuzzy search:
  "Look for anything related to appointments"

  ---
  Field Extraction Examples

  Your agent should extract:
  - Title: Main task name/action
  - Description: Additional context/details
  - Status: active (default), completed, archived
  - Priority: low, medium (default), high