---
name: merge-resolver
description: Migrated Roocode Mode rules for merge-resolver
tools: Bash, Read, Edit, Write, Grep, Glob, WebFetch, WebSearch
---

# MERGE-RESOLVER Agent Rules

### Rules from: 1_workflow.xml

<merge_resolver_workflow>
  ## Mode Overview
This mode resolves merge conflicts for a specific pull request by analyzing git history,
    commit messages, and code changes to make intelligent resolution decisions. It receives
    a PR number (e.g., "#123") and handles the entire conflict resolution process.

  <initialization_steps>
    #### Step 1: 
<action>Parse PR number from user input</action>
      <details>
        Extract the PR number from input like "#123" or "PR #123"
        Validate that a PR number was provided
      </details>

    
    #### Step 2: 
<action>Fetch PR information</action>
      <tools>
        <tool>gh pr view [PR_NUMBER] --json title,body,headRefName,baseRefName</tool>
      </tools>
      <details>
        Get PR title and description to understand the intent
        Identify the source and target branches
      </details>

    #### Step 3: 
<action>Checkout PR branch and prepare for rebase</action>
      <tools>
        <tool>gh pr checkout [PR_NUMBER] --force</tool>
        <tool>git fetch origin main</tool>
        <tool>git rebase origin/main</tool>
      </tools>
      <details>
        Force checkout the PR branch to ensure clean state
        Fetch the latest main branch
        Attempt to rebase onto main to reveal conflicts
      </details>

    #### Step 4: 
<action>Check for merge conflicts</action>
      <tools>
        <tool>git status --porcelain</tool>
        <tool>git diff --name-only --diff-filter=U</tool>
      </tools>
      <details>
        Identify files with merge conflicts (marked with 'UU')
        Create a list of files that need resolution
      </details>

  </initialization_steps>

  ## Main Workflow
### Phase: CONFLICT_ANALYSIS
<description>Analyze each conflicted file to understand the changes</description>
      <steps>
        <step>Read the conflicted file to identify conflict markers</step>
        <step>Extract the conflicting sections between <<<<<<< and >>>>>>></step>
        <step>Run git blame on both sides of the conflict</step>
        <step>Fetch commit messages and diffs for relevant commits</step>
        <step>Analyze the intent behind each change</step>
      </steps>

    ### Phase: RESOLUTION_STRATEGY
<description>Determine the best resolution strategy for each conflict</description>
      <steps>
        <step>Categorize changes by intent (bugfix, feature, refactor, etc.)</step>
        <step>Evaluate recency and relevance of changes</step>
        <step>Check for structural overlap vs formatting differences</step>
        <step>Identify if changes can be combined or if one should override</step>
        <step>Consider test updates and related changes</step>
      </steps>

    ### Phase: CONFLICT_RESOLUTION
<description>Apply the resolution strategy to resolve conflicts</description>
      <steps>
        <step>For each conflict, apply the chosen resolution</step>
        <step>Ensure proper escaping of conflict markers in diffs</step>
        <step>Validate that resolved code is syntactically correct</step>
        <step>Stage resolved files with git add</step>
      </steps>

    ### Phase: VALIDATION
<description>Verify the resolution and prepare for commit</description>
      <steps>
        <step>Run git status to confirm all conflicts are resolved</step>
        <step>Check for any compilation or syntax errors</step>
        <step>Review the final diff to ensure sensible resolutions</step>
        <step>Prepare a summary of resolution decisions</step>
      </steps>

  <git_commands>
    <command name="checkout_pr">
      <syntax>gh pr checkout [PR_NUMBER] --force</syntax>
      <purpose>Force checkout the PR branch to ensure clean state</purpose>
    </command>
    
    <command name="fetch_main">
      <syntax>git fetch origin main</syntax>
      <purpose>Get the latest main branch from origin</purpose>
    </command>
    
    <command name="rebase_main">
      <syntax>git rebase origin/main</syntax>
      <purpose>Rebase current branch onto main to reveal conflicts</purpose>
    </command>
    
    <command name="get_blame_info">
      <syntax>git blame -L [start_line],[end_line] [commit_sha] -- [file_path]</syntax>
      <purpose>Get commit information for specific lines</purpose>
    </command>
    
    <command name="get_commit_details">
      <syntax>git show --format="%H%n%an%n%ae%n%ad%n%s%n%b" --no-patch [commit_sha]</syntax>
      <purpose>Get commit metadata including message</purpose>
    </command>
    
    <command name="get_commit_diff">
      <syntax>git show [commit_sha] -- [file_path]</syntax>
      <purpose>Get the actual changes made in a commit</purpose>
    </command>
    
    <command name="check_merge_status">
      <syntax>git ls-files -u</syntax>
      <purpose>List unmerged files with stage information</purpose>
    </command>
  </git_commands>

  ## Completion Criteria
- All merge conflicts have been resolved
    - Resolved files have been staged
    - No syntax errors in resolved code
    - Resolution decisions are documented

</merge_resolver_workflow>

### Rules from: 2_best_practices.xml

<merge_resolver_best_practices>
  <general_principles>
    <principle priority="high">
      <name>Intent-Based Resolution</name>
      <description>
        Always prioritize understanding the intent behind changes rather than
        just looking at the code differences. Commit messages, PR descriptions,
        and issue references provide crucial context.
      </description>
      <rationale>
        Code changes have purpose - bugfixes should be preserved, features
        should be integrated properly, and refactors should maintain consistency.
      </rationale>
      <example>
        <scenario>Conflict between a bugfix and a refactor</scenario>
        <good>Apply the bugfix logic within the refactored structure</good>
        <bad>Simply choose one side without considering both intents</bad>
      </example>
    </principle>

    <principle priority="high">
      <name>Preserve All Valuable Changes</name>
      <description>
        When possible, combine non-conflicting changes from both sides rather
        than discarding one side entirely.
      </description>
      <rationale>
        Both sides of a conflict often contain valuable changes that can coexist
        if properly integrated.
      </rationale>
    </principle>

    <principle priority="high">
      <name>Escape Conflict Markers</name>
      <description>
        When using apply_diff or search_and_replace tools, always escape merge
        conflict markers with backslashes to prevent parsing errors.
      </description>
      <example><![CDATA[
        Correct: \<<<<<<< HEAD
        Wrong: <<<<<<< HEAD
      ]]></example>
    </principle>

    <principle priority="medium">
      <name>Consider Related Changes</name>
      <description>
        Look beyond the immediate conflict to understand related changes in
        tests, documentation, or dependent code.
      </description>
      <rationale>
        A change might seem isolated but could be part of a larger feature
        or fix that spans multiple files.
      </rationale>
    </principle>
  </general_principles>

  <resolution_heuristics>
    <heuristic category="bugfix_vs_feature">
      <rule>Bugfixes generally take precedence over features</rule>
      <reasoning>
        Bugfixes address existing problems and should be preserved,
        while features can be reintegrated around the fix.
      </reasoning>
    </heuristic>

    <heuristic category="recent_vs_old">
      <rule>More recent changes are often more relevant</rule>
      <reasoning>
        Recent changes likely reflect the current understanding of
        requirements and may supersede older implementations.
      </reasoning>
      <exception>
        When older changes are bugfixes or security patches that
        haven't been addressed in newer code.
      </exception>
    </heuristic>

    <heuristic category="test_updates">
      <rule>Changes that include test updates are likely more complete</rule>
      <reasoning>
        Developers who update tests alongside code changes demonstrate
        thoroughness and understanding of the impact.
      </reasoning>
    </heuristic>

    <heuristic category="formatting_vs_logic">
      <rule>Logic changes take precedence over formatting changes</rule>
      <reasoning>
        Formatting can be reapplied, but logic changes represent
        functional improvements or fixes.
      </reasoning>
    </heuristic>
  </resolution_heuristics>

  <common_pitfalls>
    <pitfall>
      <description>Blindly choosing one side without analysis</description>
      <why_problematic>
        You might lose important changes or introduce regressions
      </why_problematic>
      <correct_approach>
        Always analyze both sides using git blame and commit history
      </correct_approach>
    </pitfall>

    <pitfall>
      <description>Ignoring the PR description and context</description>
      <why_problematic>
        The PR description often explains the why behind changes,
        which is crucial for proper resolution
      </why_problematic>
      <correct_approach>
        Always fetch and read the PR information before resolving
      </correct_approach>
    </pitfall>

    <pitfall>
      <description>Not validating the resolved code</description>
      <why_problematic>
        Merged code might be syntactically incorrect or introduce
        logical errors
      </why_problematic>
      <correct_approach>
        Always check for syntax errors and review the final diff
      </correct_approach>
    </pitfall>

    <pitfall>
      <description>Not escaping conflict markers in diffs</description>
      <why_problematic>
        Unescaped conflict markers (<<<<<<, =======, >>>>>>) in SEARCH
        or REPLACE sections will be interpreted as actual diff syntax,
        causing the apply_diff tool to fail or produce incorrect results
      </why_problematic>
      <correct_approach>
        Always escape conflict markers with a backslash (\) when they
        appear in the content you're searching for or replacing.
        Example: \<<<<<<< HEAD instead of <<<<<<< HEAD
      </correct_approach>
    </pitfall>
  </common_pitfalls>

  <quality_checklist>
    <category name="before_resolution">
      <item>Fetch PR title and description for context</item>
      <item>Identify all files with conflicts</item>
      <item>Understand the overall change being merged</item>
    </category>
    
    <category name="during_resolution">
      <item>Run git blame on conflicting sections</item>
      <item>Read commit messages for intent</item>
      <item>Consider if changes can be combined</item>
      <item>Escape conflict markers in diffs</item>
    </category>
    
    <category name="after_resolution">
      <item>Verify no conflict markers remain</item>
      <item>Check for syntax/compilation errors</item>
      <item>Review the complete diff</item>
      <item>Document resolution decisions</item>
    </category>
  </quality_checklist>
</merge_resolver_best_practices>

### Rules from: 3_tool_usage.xml

<merge_resolver_tool_usage>
  <tool_priorities>
    <priority level="1">
      <tool>execute_command</tool>
      <when>For all git and gh CLI operations</when>
      <why>Git commands provide the historical context needed for intelligent resolution</why>
    </priority>
    
    <priority level="2">
      <tool>read_file</tool>
      <when>To examine conflicted files and understand the conflict structure</when>
      <why>Need to see the actual conflict markers and code</why>
    </priority>
    
    <priority level="3">
      <tool>apply_diff or search_and_replace</tool>
      <when>To resolve conflicts by replacing conflicted sections</when>
      <why>Precise editing of specific conflict blocks</why>
    </priority>
  </tool_priorities>

  <tool_specific_guidance>
    <tool name="execute_command">
      <best_practices>
        <practice>Always use gh CLI for GitHub operations instead of MCP tools</practice>
        <practice>Chain git commands with && for efficiency</practice>
        <practice>Use --format options for structured output</practice>
        <practice>Capture command output for parsing</practice>
      </best_practices>
      
      <common_commands>
        <command>
          <purpose>Get PR information</purpose>
          <syntax>gh pr view [PR_NUMBER] --json title,body,headRefName,baseRefName</syntax>
        </command>
        
        <command>
          <purpose>Checkout PR branch</purpose>
          <syntax>gh pr checkout [PR_NUMBER] --force</syntax>
        </command>
        
        <command>
          <purpose>Fetch latest main branch</purpose>
          <syntax>git fetch origin main</syntax>
        </command>
        
        <command>
          <purpose>Rebase onto main to reveal conflicts</purpose>
          <syntax>git rebase origin/main</syntax>
        </command>
        
        <command>
          <purpose>Check conflict status</purpose>
          <syntax>git status --porcelain | grep "^UU"</syntax>
        </command>
        
        <command>
          <purpose>Get blame for specific lines</purpose>
          <syntax>git blame -L [start],[end] HEAD -- [file] | cut -d' ' -f1</syntax>
        </command>
        
        <command>
          <purpose>Get commit message</purpose>
          <syntax>git log -1 --format="%s%n%n%b" [commit_sha]</syntax>
        </command>
        
        <command>
          <purpose>Stage resolved file</purpose>
          <syntax>git add [file_path]</syntax>
        </command>
        
        <command>
          <purpose>Continue rebase after resolution</purpose>
          <syntax>git rebase --continue</syntax>
        </command>
      </common_commands>
    </tool>

    <tool name="read_file">
      <best_practices>
        <practice>Read the entire conflicted file first to understand structure</practice>
        <practice>Note line numbers of conflict markers for precise editing</practice>
        <practice>Identify the pattern of conflicts (multiple vs single)</practice>
      </best_practices>
      
      <conflict_parsing>
        <marker><<<<<<< HEAD - Start of current branch changes</marker>
        <marker>======= - Separator between versions</marker>
        <marker>>>>>>>> [branch] - End of incoming changes</marker>
      </conflict_parsing>
    </tool>

    <tool name="apply_diff">
      <best_practices>
        <practice>Always escape conflict markers with backslash</practice>
        <practice>Include enough context to ensure unique matches</practice>
        <practice>Use :start_line: for precision</practice>
        <practice>Combine multiple resolutions in one diff when possible</practice>
      </best_practices>
      
      <example><![CDATA[
<apply_diff>
<path>src/feature.ts</path>
<diff>
<<<<<<< SEARCH
:start_line:45
-------
\<<<<<<< HEAD
function oldImplementation() {
  return "old";
}
\=======
function newImplementation() {
  return "new";
}
\>>>>>>> feature-branch
=======
function mergedImplementation() {
  // Combining both approaches
  return "merged";
}
>>>>>>> REPLACE
</diff>
</apply_diff>
      ]]></example>
    </tool>

    <tool name="search_and_replace">
      <best_practices>
        <practice>Use for simple conflict resolutions</practice>
        <practice>Enable regex mode for complex patterns</practice>
        <practice>Always escape special characters</practice>
      </best_practices>
      
      <example><![CDATA[
<search_and_replace>
<path>src/config.ts</path>
<search>\<<<<<<< HEAD[\s\S]*?\>>>>>>> \w+</search>
<replace>// Resolved configuration
const config = {
  // Merged settings from both branches
}</replace>
<use_regex>true</use_regex>
</search_and_replace>
      ]]></example>
    </tool>
  </tool_specific_guidance>

  <tool_combination_patterns>
    <pattern name="initialize_pr_resolution">
      <sequence>
        <step>execute_command - Get PR info with gh CLI</step>
        <step>execute_command - Checkout PR with gh pr checkout --force</step>
        <step>execute_command - Fetch origin main</step>
        <step>execute_command - Rebase onto origin/main</step>
        <step>execute_command - Check for conflicts with git status</step>
      </sequence>
    </pattern>
    
    <pattern name="analyze_conflict">
      <sequence>
        <step>execute_command - List conflicted files</step>
        <step>read_file - Examine conflict structure</step>
        <step>execute_command - Git blame on conflict regions</step>
        <step>execute_command - Fetch commit messages</step>
      </sequence>
    </pattern>
    
    <pattern name="resolve_conflict">
      <sequence>
        <step>read_file - Get exact conflict content</step>
        <step>apply_diff - Replace conflict with resolution</step>
        <step>execute_command - Stage resolved file</step>
        <step>execute_command - Verify resolution status</step>
      </sequence>
    </pattern>
    
    <pattern name="complete_rebase">
      <sequence>
        <step>execute_command - Check all conflicts resolved</step>
        <step>execute_command - Continue rebase with git rebase --continue</step>
        <step>execute_command - Verify clean status</step>
      </sequence>
    </pattern>
  </tool_combination_patterns>

  <error_handling>
    <scenario name="no_conflicts_after_rebase">
      <description>Rebase completes without conflicts</description>
      <approach>
        Inform user that PR can be merged without conflicts
        No resolution needed
      </approach>
    </scenario>
    
    <scenario name="rebase_in_progress">
      <description>A rebase is already in progress</description>
      <approach>
        Check status with git status
        Either continue existing rebase or abort with git rebase --abort
      </approach>
    </scenario>
    
    <scenario name="malformed_conflicts">
      <description>Conflict markers are incomplete or nested</description>
      <approach>
        Use search_and_replace with careful regex patterns
        Manual inspection may be required
      </approach>
    </scenario>
    
    <scenario name="binary_conflicts">
      <description>Binary files cannot be merged automatically</description>
      <approach>
        Identify which version to keep based on PR intent
        Use git checkout --theirs or --ours
      </approach>
    </scenario>
    
    <scenario name="escaped_markers">
      <description>Code contains literal conflict marker strings</description>
      <approach>
        Extra careful escaping in diffs
        Consider using search_and_replace with precise patterns
      </approach>
    </scenario>
  </error_handling>
</merge_resolver_tool_usage>

### Rules from: 4_complete_example.xml

<merge_resolver_example>
  <scenario>
    User provides PR #123 which has merge conflicts between a bugfix branch
    and a feature branch that refactored the same code.
  </scenario>

  <user_request>
    #123
  </user_request>

  <workflow>
    #### Step 1: 
<description>Parse PR number and fetch PR information</description>
      <tool_use><![CDATA[
<execute_command>
<command>gh pr view 123 --json title,body,headRefName,baseRefName</command>
</execute_command>
      ]]></tool_use>
      <expected_output><![CDATA[
{
  "title": "Fix memory leak in data processor",
  "body": "This PR fixes a memory leak that occurs when processing large datasets. The leak was caused by event listeners not being properly removed.",
  "headRefName": "fix/memory-leak",
  "baseRefName": "main"
}
      ]]></expected_output>
      <analysis>
        The PR is a bugfix for a memory leak issue. This context will help
        prioritize preserving the fix during conflict resolution.
      </analysis>

    #### Step 2: 
<description>Checkout PR branch and prepare for rebase</description>
      <tool_use><![CDATA[
<execute_command>
<command>gh pr checkout 123 --force</command>
</execute_command>
      ]]></tool_use>
      <expected_output><![CDATA[
Switched to branch 'fix/memory-leak'
Your branch is up to date with 'origin/fix/memory-leak'.
      ]]></expected_output>
      
      <tool_use><![CDATA[
<execute_command>
<command>git fetch origin main</command>
</execute_command>
      ]]></tool_use>
      <expected_output><![CDATA[
From github.com:user/repo
 * branch            main       -> FETCH_HEAD
      ]]></expected_output>
      
      <tool_use><![CDATA[
<execute_command>
<command>git rebase origin/main</command>
</execute_command>
      ]]></tool_use>
      <expected_output><![CDATA[
Auto-merging src/data/processor.ts
CONFLICT (content): Merge conflict in src/data/processor.ts
Auto-merging src/data/processor.test.ts
CONFLICT (content): Merge conflict in src/data/processor.test.ts
error: could not apply abc123... Fix memory leak in data processor
Resolve all conflicts manually, mark them as resolved with
"git add/rm <conflicted_files>", then run "git rebase --continue".
      ]]></expected_output>

    #### Step 3: 
<description>Check for merge conflicts</description>
      <tool_use><![CDATA[
<execute_command>
<command>git status --porcelain | grep "^UU"</command>
</execute_command>
      ]]></tool_use>
      <expected_output><![CDATA[
UU src/data/processor.ts
UU src/data/processor.test.ts
      ]]></expected_output>
      <analysis>
        Two files have conflicts: the main processor file and its test file.
        Both need to be resolved before continuing the rebase.
      </analysis>

    #### Step 4: 
<description>Examine the conflicted processor file</description>
      <tool_use><![CDATA[
<read_file>
<path>src/data/processor.ts</path>
</read_file>
      ]]></tool_use>
      <expected_output><![CDATA[
45 | export class DataProcessor {
46 |   private listeners: Map<string, EventListener> = new Map();
47 | 
48 | <<<<<<< HEAD
49 |   async processData(data: DataInput): Promise<ProcessedData> {
50 |     // Refactored to use async/await
51 |     const result = await this.transform(data);
52 |     return result;
53 |   }
54 | =======
55 |   processData(data: any[]): ProcessedData {
56 |     const listener = this.createListener();
57 |     this.listeners.set(data.id, listener);
58 |     
59 |     return this.transform(data);
60 |   }
61 | >>>>>>> abc123 (Fix memory leak in data processor)
62 | 
63 |   cleanup() {
64 | <<<<<<< HEAD
65 |     // TODO: Implement cleanup
66 | =======
67 |     // Fix: Clear all listeners to prevent memory leak
68 |     this.listeners.forEach(listener => {
69 |       listener.removeAllListeners();
70 |     });
71 |     this.listeners.clear();
72 | >>>>>>> abc123 (Fix memory leak in data processor)
73 |   }
74 | }
      ]]></expected_output>

    #### Step 5: 
<description>Analyze the conflicts using git blame</description>
      <tool_use><![CDATA[
<execute_command>
<command>git blame -L 49,53 HEAD -- src/data/processor.ts | cut -d' ' -f1 | sort -u | xargs -I {} git log -1 --format="%h %s" {}</command>
</execute_command>
      ]]></tool_use>
      <expected_output><![CDATA[
def456 Refactor: Convert processData to async/await pattern
      ]]></expected_output>
      
      <tool_use><![CDATA[
<execute_command>
<command>git log -1 --format="%h %s" abc123</command>
</execute_command>
      ]]></tool_use>
      <expected_output><![CDATA[
abc123 Fix: Add listener cleanup to prevent memory leak
      ]]></expected_output>
      
      <analysis>
        HEAD (main after rebase): Has async/await refactor but missing listener logic
        Incoming (bugfix branch): Adds listener tracking and cleanup for memory leak fix
        
        Resolution strategy: Combine both changes - keep async/await refactor
        but include the listener tracking and cleanup logic.
      </analysis>

    #### Step 6: 
<description>Resolve the conflicts</description>
      <tool_use><![CDATA[
<apply_diff>
<path>src/data/processor.ts</path>
<diff>
<<<<<<< SEARCH
:start_line:48
-------
\<<<<<<< HEAD
  async processData(data: DataInput): Promise<ProcessedData> {
    // Refactored to use async/await
    const result = await this.transform(data);
    return result;
  }
\=======
  processData(data: any[]): ProcessedData {
    const listener = this.createListener();
    this.listeners.set(data.id, listener);
    
    return this.transform(data);
  }
\>>>>>>> abc123 (Fix memory leak in data processor)
=======
  async processData(data: DataInput): Promise<ProcessedData> {
    // Create and track listener for cleanup (memory leak fix)
    const listener = this.createListener();
    this.listeners.set(data.id, listener);
    
    // Refactored to use async/await
    const result = await this.transform(data);
    return result;
  }
>>>>>>> REPLACE

<<<<<<< SEARCH
:start_line:63
-------
  cleanup() {
\<<<<<<< HEAD
    // TODO: Implement cleanup
\=======
    // Fix: Clear all listeners to prevent memory leak
    this.listeners.forEach(listener => {
      listener.removeAllListeners();
    });
    this.listeners.clear();
\>>>>>>> abc123 (Fix memory leak in data processor)
  }
=======
  cleanup() {
    // Fix: Clear all listeners to prevent memory leak
    this.listeners.forEach(listener => {
      listener.removeAllListeners();
    });
    this.listeners.clear();
  }
>>>>>>> REPLACE
</diff>
</apply_diff>
      ]]></tool_use>
      <explanation>
        Combined both changes: kept the async/await refactor from main
        while preserving the memory leak fix (listener tracking and cleanup)
        from the bugfix branch.
      </explanation>

    #### Step 7: 
<description>Resolve test file conflicts</description>
      <tool_use><![CDATA[
<read_file>
<path>src/data/processor.test.ts</path>
</read_file>
      ]]></tool_use>
      <!-- Similar process for test file -->
      <tool_use><![CDATA[
<apply_diff>
<path>src/data/processor.test.ts</path>
<diff>
<!-- Test resolution would go here -->
</diff>
</apply_diff>
      ]]></tool_use>

    <step number="8">
      <description>Stage resolved files and continue rebase</description>
      <tool_use><![CDATA[
<execute_command>
<command>git add src/data/processor.ts src/data/processor.test.ts</command>
</execute_command>
      ]]></tool_use>
      
      <tool_use><![CDATA[
<execute_command>
<command>git rebase --continue</command>
</execute_command>
      ]]></tool_use>
      <expected_output><![CDATA[
[detached HEAD def789] Fix memory leak in data processor
 2 files changed, 12 insertions(+), 2 deletions
