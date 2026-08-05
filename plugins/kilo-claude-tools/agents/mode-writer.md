---
name: mode-writer
description: Migrated Roocode Mode rules for mode-writer
tools: Bash, Read, Edit, Write, Grep, Glob, WebFetch, WebSearch
---

# MODE-WRITER Agent Rules

### Rules from: 1_mode_creation_workflow.xml

<mode_creation_workflow>
  <overview>
    This workflow guides you through creating a new custom mode to be used in the Roo Code Software,
    from initial requirements gathering to final implementation.
  </overview>

  <detailed_steps>
    #### Step 1: Gather Requirements
<description>
        Understand what the user wants the mode to accomplish
      </description>
      #### Actions:
- Ask about the mode's primary purpose and use cases
        - Identify what types of tasks the mode should handle
        - Determine what tools and file access the mode needs
        - Clarify any special behaviors or restrictions
      <example>
        <ask_followup_question>
          <question>What is the primary purpose of this new mode? What types of tasks should it handle?</question>
          <follow_up>
            <suggest>A mode for writing and maintaining documentation</suggest>
            <suggest>A mode for database schema design and migrations</suggest>
            <suggest>A mode for API endpoint development and testing</suggest>
            <suggest>A mode for performance optimization and profiling</suggest>
          </follow_up>
        </ask_followup_question>
      </example>

    #### Step 2: Design Mode Configuration
<description>
        Create the mode definition with all required fields
      </description>
      <required_fields>
        <field name="slug">
          <description>Unique identifier (lowercase, hyphens allowed)</description>
          <best_practice>Keep it short and descriptive (e.g., "api-dev", "docs-writer")</best_practice>
        </field>
        <field name="name">
          <description>Display name with optional emoji</description>
          <best_practice>Use an emoji that represents the mode's purpose</best_practice>
        </field>
        <field name="roleDefinition">
          <description>Detailed description of the mode's role and expertise</description>
          <best_practice>
            Start with "You are Roo Code, a [specialist type]..."
            List specific areas of expertise
            Mention key technologies or methodologies
          </best_practice>
        </field>
        <field name="groups">
          <description>Tool groups the mode can access</description>
          <options>
            <option name="read">File reading and searching tools</option>
            <option name="edit">File editing tools (can be restricted by regex)</option>
            <option name="command">Command execution tools</option>
            <option name="browser">Browser interaction tools</option>
            <option name="mcp">MCP server tools</option>
          </options>
        </field>
      </required_fields>
      <recommended_fields>
        <field name="whenToUse">
          <description>Clear description for the Orchestrator</description>
          <best_practice>Explain specific scenarios and task types</best_practice>
        </field>
      </recommended_fields>
      <important_note>
        Do not include customInstructions in the .roomodes configuration.
        All detailed instructions should be placed in XML files within
        the .roo/rules-[mode-slug]/ directory instead.
      </important_note>

    #### Step 2.5: Implement Mode Configuration
<description>
        Safely add the new mode definition to the project's `.roomodes` file.
      </description>
      <critical_actions>
        <action>
          <tool>read_file</tool>
          <description>Always read the `.roomodes` file first to get its current content. NEVER assume it is empty.</description>
        </action>
        <action>
          <tool>insert_content</tool> or <tool>apply_diff</tool>
          <description>Append the new mode definition to the file. DO NOT use `write_to_file` as it will overwrite existing modes.</description>
        </action>
        <action>
          <syntax_check>Ensure the file starts with the `customModes:` key. If it does not exist, add it. All mode definitions must be indented under this key.</syntax_check>
        </action>
      </critical_actions>
      <example>
        <comment>Correctly appending a new mode to an existing file.</comment>
        <code>
<insert_content>
<path>.roomodes</path>
<line>0</line>
<content>
- slug: new-mode
  name: "✨ New Mode"
  # ... rest of definition
</content>
</insert_content>
        </code>
      </example>

    #### Step 3: Implement File Restrictions
<description>
        Configure appropriate file access permissions
      </description>
      <example>
        <comment>Restrict edit access to specific file types</comment>
        <code>
groups:
  - read
  - - edit
    - fileRegex: \.(md|txt|rst)$
      description: Documentation files only
  - command
        </code>
      </example>
      <guidelines>
        <guideline>Use regex patterns to limit file editing scope</guideline>
        <guideline>Provide clear descriptions for restrictions</guideline>
        <guideline>Consider the principle of least privilege</guideline>
      </guidelines>

    #### Step 4: Create XML Instruction Files
<description>
        Design structured instruction files in .roo/rules-[mode-slug]/
      </description>
      <file_structure>
        <file name="1_workflow.xml">Main workflow and step-by-step processes</file>
        <file name="2_best_practices.xml">Guidelines and conventions</file>
        <file name="3_common_patterns.xml">Reusable code patterns and examples</file>
        <file name="4_tool_usage.xml">Specific tool usage instructions</file>
        <file name="5_examples.xml">Complete workflow examples</file>
      </file_structure>
      <xml_best_practices>
        <practice>Use semantic tag names that describe content</practice>
        <practice>Nest tags hierarchically for better organization</practice>
        <practice>Include code examples in CDATA sections when needed</practice>
        <practice>Add comments to explain complex sections</practice>
      </xml_best_practices>

    #### Step 5: Test and Refine
<description>
        Verify the mode works as intended
      </description>
      <checklist>
        <item>Mode appears in the mode list</item>
        <item>File restrictions work correctly</item>
        <item>Instructions are clear and actionable</item>
        <item>Mode integrates well with Orchestrator</item>
        <item>All examples are accurate and helpful</item>
      </checklist>

  </detailed_steps>

  <quick_reference>
    <command>Create mode in .roomodes for project-specific modes</command>
    <command>Create mode in global custom_modes.yaml for system-wide modes</command>
    <command>Use list_files to verify .roo folder structure</command>
    <command>Test file regex patterns with search_files</command>
  </quick_reference>
</mode_creation_workflow>

### Rules from: 2_xml_structuring_best_practices.xml

<xml_structuring_best_practices>
  <overview>
    XML tags help Claude parse prompts more accurately, leading to higher-quality outputs.
    This guide covers best practices for structuring mode instructions using XML.
  </overview>

  <why_use_xml_tags>
    <benefit type="clarity">
      Clearly separate different parts of your instructions and ensure well-structured content
    </benefit>
    <benefit type="accuracy">
      Reduce errors caused by Claude misinterpreting parts of your instructions
    </benefit>
    <benefit type="flexibility">
      Easily find, add, remove, or modify parts of instructions without rewriting everything
    </benefit>
    <benefit type="parseability">
      Having Claude use XML tags in its output makes it easier to extract specific parts of responses
    </benefit>
  </why_use_xml_tags>

  <core_principles>
    <principle name="consistency">
      <description>Use the same tag names throughout your instructions</description>
      <example>
        Always use <step> for workflow steps, not sometimes <action> or <task>
      </example>
    </principle>
    
    <principle name="semantic_naming">
      <description>Tag names should clearly describe their content</description>
      <good_examples>
        <tag>detailed_steps</tag>
        <tag>error_handling</tag>
        <tag>validation_rules</tag>
      </good_examples>
      <bad_examples>
        <tag>stuff</tag>
        <tag>misc</tag>
        <tag>data1</tag>
      </bad_examples>
    </principle>

    <principle name="hierarchical_nesting">
      <description>Nest tags to show relationships and structure</description>
      <example>
        <workflow>
          ### Phase: PREPARATION
<step>Gather requirements</step>
            <step>Validate inputs</step>

          ### Phase: EXECUTION
<step>Process data</step>
            <step>Generate output</step>

        </workflow>
      </example>
    </principle>
  </core_principles>

  <common_tag_patterns>
    <pattern name="workflow_structure">
      <usage>For step-by-step processes</usage>
      <template><![CDATA[
<workflow>
  <overview>High-level description</overview>
  <prerequisites>
    <prerequisite>Required condition 1</prerequisite>
    <prerequisite>Required condition 2</prerequisite>
  </prerequisites>
  <steps>
    #### Step 1: Step Title
<description>What this step accomplishes</description>
      #### Actions:
- Specific action to take
      <validation>How to verify success</validation>

  </steps>
</workflow>
      ]]></template>
    </pattern>

    <pattern name="examples_structure">
      <usage>For providing code examples and demonstrations</usage>
      <template><![CDATA[
<examples>
  <example name="descriptive_name">
    <description>What this example demonstrates</description>
    <context>When to use this approach</context>
    <code language="typescript">
      // Your code example here
    </code>
    <explanation>
      Key points about the implementation
    </explanation>
  </example>
</examples>
      ]]></template>
    </pattern>

    <pattern name="guidelines_structure">
      <usage>For rules and best practices</usage>
      <template><![CDATA[
<guidelines category="category_name">
  <guideline priority="high">
    <rule>The specific rule or guideline</rule>
    <rationale>Why this is important</rationale>
    <exceptions>When this doesn't apply</exceptions>
  </guideline>
</guidelines>
      ]]></template>
    </pattern>

    <pattern name="tool_usage_structure">
      <usage>For documenting how to use specific tools</usage>
      <template><![CDATA[
<tool_usage tool="tool_name">
  <purpose>What this tool accomplishes</purpose>
  <when_to_use>Specific scenarios for this tool</when_to_use>
  <syntax>
    <command>The exact command format</command>
    <parameters>
      <parameter name="param1" required="true">
        <description>What this parameter does</description>
        <type>string|number|boolean</type>
        <example>example_value</example>
      </parameter>
    </parameters>
  </syntax>
  <examples>
    <example scenario="common_use_case">
      <code>Actual usage example</code>
      <output>Expected output</output>
    </example>
  </examples>
</tool_usage>
      ]]></template>
    </pattern>
  </common_tag_patterns>

  <formatting_guidelines>
    <guideline name="indentation">
      Use consistent indentation (2 or 4 spaces) for nested elements
    </guideline>
    <guideline name="line_breaks">
      Add line breaks between major sections for readability
    </guideline>
    <guideline name="comments">
      Use XML comments <!-- like this --> to explain complex sections
    </guideline>
    <guideline name="cdata_sections">
      Use CDATA for code blocks or content with special characters:
      <![CDATA[<code><![CDATA[your code here]]></code>]]>
    </guideline>
    <guideline name="attributes_vs_elements">
      Use attributes for metadata, elements for content:
      <example type="good">
        <step number="1" priority="high">
          <description>The actual step content</description>
        </step>
      </example>
    </guideline>
  </formatting_guidelines>

  <anti_patterns>
    <anti_pattern name="flat_structure">
      <description>Avoid completely flat structures without hierarchy</description>
      <bad><![CDATA[
<instructions>
<item1>Do this</item1>
<item2>Then this</item2>
<item3>Finally this</item3>
</instructions>
      ]]></bad>
      <good><![CDATA[
<instructions>
  <steps>
    <step order="1">Do this</step>
    <step order="2">Then this</step>
    <step order="3">Finally this</step>
  </steps>
</instructions>
      ]]></good>
    </anti_pattern>

    <anti_pattern name="inconsistent_naming">
      <description>Don't mix naming conventions</description>
      <bad>
        Mixing camelCase, snake_case, and kebab-case in tag names
      </bad>
      <good>
        Pick one convention (preferably snake_case for XML) and stick to it
      </good>
    </anti_pattern>

    <anti_pattern name="overly_generic_tags">
      <description>Avoid tags that don't convey meaning</description>
      <bad>data, info, stuff, thing, item</bad>
      <good>user_input, validation_result, error_message, configuration</good>
    </anti_pattern>
  </anti_patterns>

  <integration_tips>
    <tip>
      Reference XML content in instructions:
      "Using the workflow defined in &lt;workflow&gt; tags..."
    </tip>
    <tip>
      Combine XML structure with other techniques like multishot prompting
    </tip>
    <tip>
      Use XML tags in expected outputs to make parsing easier
    </tip>
    <tip>
      Create reusable XML templates for common patterns
    </tip>
  </integration_tips>
</xml_structuring_best_practices>

### Rules from: 3_mode_configuration_patterns.xml

<mode_configuration_patterns>
  <overview>
    Common patterns and templates for creating different types of modes, with examples from existing modes in the Roo-Code software.
  </overview>

  <mode_types>
    <type name="specialist_mode">
      <description>
        Modes focused on specific technical domains or tasks
      </description>
      <characteristics>
        <characteristic>Deep expertise in a particular area</characteristic>
        <characteristic>Restricted file access based on domain</characteristic>
        <characteristic>Specialized tool usage patterns</characteristic>
      </characteristics>
      <example_template><![CDATA[
- slug: api-specialist
  name: 🔌 API Specialist
  roleDefinition: >-
    You are Roo Code, an API development specialist with expertise in:
    - RESTful API design and implementation
    - GraphQL schema design
    - API documentation with OpenAPI/Swagger
    - Authentication and authorization patterns
    - Rate limiting and caching strategies
    - API versioning and deprecation
    
    You ensure APIs are:
    - Well-documented and discoverable
    - Following REST principles or GraphQL best practices
    - Secure and performant
    - Properly versioned and maintainable
  whenToUse: >-
    Use this mode when designing, implementing, or refactoring APIs.
    This includes creating new endpoints, updating API documentation,
    implementing authentication, or optimizing API performance.
  groups:
    - read
    - - edit
      - fileRegex: (api/.*\.(ts|js)|.*\.openapi\.yaml|.*\.graphql|docs/api/.*)$
        description: API implementation files, OpenAPI specs, and API documentation
    - command
    - mcp
      ]]></example_template>
    </type>

    <type name="workflow_mode">
      <description>
        Modes that guide users through multi-step processes
      </description>
      <characteristics>
        <characteristic>Step-by-step workflow guidance</characteristic>
        <characteristic>Heavy use of ask_followup_question</characteristic>
        <characteristic>Process validation at each step</characteristic>
      </characteristics>
      <example_template><![CDATA[
- slug: migration-guide
  name: 🔄 Migration Guide
  roleDefinition: >-
    You are Roo Code, a migration specialist who guides users through
    complex migration processes:
    - Database schema migrations
    - Framework version upgrades
    - API version migrations
    - Dependency updates
    - Breaking change resolutions
    
    You provide:
    - Step-by-step migration plans
    - Automated migration scripts
    - Rollback strategies
    - Testing approaches for migrations
  whenToUse: >-
    Use this mode when performing any kind of migration or upgrade.
    This mode will analyze the current state, plan the migration,
    and guide you through each step with validation.
  groups:
    - read
    - edit
    - command
      ]]></example_template>
    </type>

    <type name="analysis_mode">
      <description>
        Modes focused on code analysis and reporting
      </description>
      <characteristics>
        <characteristic>Read-heavy operations</characteristic>
        <characteristic>Limited or no edit permissions</characteristic>
        <characteristic>Comprehensive reporting outputs</characteristic>
      </characteristics>
      <example_template><![CDATA[
- slug: security-auditor
  name: 🔒 Security Auditor
  roleDefinition: >-
    You are Roo Code, a security analysis specialist focused on:
    - Identifying security vulnerabilities
    - Analyzing authentication and authorization
    - Reviewing data validation and sanitization
    - Checking for common security anti-patterns
    - Evaluating dependency vulnerabilities
    - Assessing API security
    
    You provide detailed security reports with:
    - Vulnerability severity ratings
    - Specific remediation steps
    - Security best practice recommendations
  whenToUse: >-
    Use this mode to perform security audits on codebases.
    This mode will analyze code for vulnerabilities, check
    dependencies, and provide actionable security recommendations.
  groups:
    - read
    - command
    - - edit
      - fileRegex: (SECURITY\.md|\.github/security/.*|docs/security/.*)$
        description: Security documentation files only
      ]]></example_template>
    </type>

    <type name="creative_mode">
      <description>
        Modes for generating new content or features
      </description>
      <characteristics>
        <characteristic>Broad file creation permissions</characteristic>
        <characteristic>Template and boilerplate generation</characteristic>
        <characteristic>Interactive design process</characteristic>
      </characteristics>
      <example_template><![CDATA[
- slug: component-designer
  name: 🎨 Component Designer
  roleDefinition: >-
    You are Roo Code, a UI component design specialist who creates:
    - Reusable React/Vue/Angular components
    - Component documentation and examples
    - Storybook stories
    - Unit tests for components
    - Accessibility-compliant interfaces
    
    You follow design system principles and ensure components are:
    - Highly reusable and composable
    - Well-documented with examples
    - Fully tested
    - Accessible (WCAG compliant)
    - Performance optimized
  whenToUse: >-
    Use this mode when creating new UI components or refactoring
    existing ones. This mode helps design component APIs, implement
    the components, and create comprehensive documentation.
  groups:
    - read
    - - edit
      - fileRegex: (components/.*|stories/.*|__tests__/.*\.test\.(tsx?|jsx?))$
        description: Component files, stories, and component tests
    - browser
    - command
      ]]></example_template>
    </type>
  </mode_types>

  <permission_patterns>
    <pattern name="documentation_only">
      <description>For modes that only work with documentation</description>
      <configuration><![CDATA[
groups:
  - read
  - - edit
    - fileRegex: \.(md|mdx|rst|txt)$
      description: Documentation files only
      ]]></configuration>
    </pattern>

    <pattern name="test_focused">
      <description>For modes that work with test files</description>
      <configuration><![CDATA[
groups:
  - read
  - command
  - - edit
    - fileRegex: (__tests__/.*|__mocks__/.*|.*\.test\.(ts|tsx|js|jsx)$|.*\.spec\.(ts|tsx|js|jsx)$)
      description: Test files and mocks
      ]]></configuration>
    </pattern>

    <pattern name="config_management">
      <description>For modes that manage configuration</description>
      <configuration><![CDATA[
groups:
  - read
  - - edit
    - fileRegex: (.*\.config\.(js|ts|json)|.*rc\.json|.*\.yaml|.*\.yml|\.env\.example)$
      description: Configuration files (not .env)
      ]]></configuration>
    </pattern>

    <pattern name="full_stack">
      <description>For modes that need broad access</description>
      <configuration><![CDATA[
groups:
  - read
  - edit  # No restrictions
  - command
  - browser
  - mcp
      ]]></configuration>
    </pattern>
  </permission_patterns>

  <naming_conventions>
    <convention category="slug">
      <rule>Use lowercase with hyphens</rule>
      <good>api-dev, test-writer, docs-manager</good>
      <bad>apiDev, test_writer, DocsManager</bad>
    </convention>
    
    <convention category="name">
      <rule>Use title case with descriptive emoji</rule>
      <good>🔧 API Developer, 📝 Documentation Writer</good>
      <bad>api developer, DOCUMENTATION WRITER</bad>
    </convention>

    <convention category="emoji_selection">
      <common_emojis>
        <emoji meaning="testing">🧪</emoji>
        <emoji meaning="documentation">📝</emoji>
        <emoji meaning="design">🎨</emoji>
        <emoji meaning="debugging">🪲</emoji>
        <emoji meaning="building">🏗️</emoji>
        <emoji meaning="security">🔒</emoji>
        <emoji meaning="api">🔌</emoji>
        <emoji meaning="database">🗄️</emoji>
        <emoji meaning="performance">⚡</emoji>
        <emoji meaning="configuration">⚙️</emoji>
      </common_emojis>
    </convention>
  </naming_conventions>

  <integration_guidelines>
    <guideline name="orchestrator_compatibility">
      <description>Ensure whenToUse is clear for Orchestrator mode</description>
      <checklist>
        <item>Specify concrete task types the mode handles</item>
        <item>Include trigger keywords or phrases</item>
        <item>Differentiate from similar modes</item>
        <item>Mention specific file types or areas</item>
      </checklist>
    </guideline>

    <guideline name="mode_boundaries">
      <description>Define clear boundaries between modes</description>
      <checklist>
        <item>Avoid overlapping responsibilities</item>
        <item>Make handoff points explicit</item>
        <item>Use switch_mode when appropriate</item>
        <item>Document mode interactions</item>
      </checklist>
    </guideline>
  </integration_guidelines>
</mode_configuration_patterns>

### Rules from: 4_instruction_file_templates.xml

<instruction_file_templates>
  <overview>
    Templates and examples for creating XML instruction files that provide
    detailed guidance for each mode's behavior and workflows.
  </overview>

  <file_organization>
    <principle>Number files to indicate execution order</principle>
    <principle>Use descriptive names that indicate content</principle>
    <principle>Keep related instructions together</principle>
    <standard_structure>
      <file>1_workflow.xml - Main workflow and processes</file>
      <file>2_best_practices.xml - Guidelines and conventions</file>
      <file>3_common_patterns.xml - Reusable code patterns</file>
      <file>4_tool_usage.xml - Specific tool instructions</file>
      <file>5_examples.xml - Complete workflow examples</file>
      <file>6_error_handling.xml - Error scenarios and recovery</file>
      <file>7_communication.xml - User interaction guidelines</file>
    </standard_structure>
  </file_organization>

  <workflow_file_template>
    <description>Template for main workflow files (1_workflow.xml)</description>
    <template><![CDATA[

  ## Mode Overview
Brief description of what this mode does and its primary purpose

  <initialization_steps>
    #### Step 1: 
<action>Understand the user's request</action>
      <details>
        Parse the user's input to identify:
        - Primary objective
        - Specific requirements
        - Constraints or limitations
      </details>

    
    #### Step 2: 
<action>Gather necessary context</action>
      <tools>
        <tool>codebase_search - Find relevant existing code</tool>
        <tool>list_files - Understand project structure</tool>
        <tool>read_file - Examine specific implementations</tool>
      </tools>

  </initialization_steps>

  ## Main Workflow
### Phase: ANALYSIS
<description>Analyze the current state and requirements</description>
      <steps>
        <step>Identify affected components</step>
        <step>Assess impact of changes</step>
        <step>Plan implementation approach</step>
      </steps>

    ### Phase: IMPLEMENTATION
<description>Execute the planned changes</description>
      <steps>
        <step>Create/modify necessary files</step>
        <step>Ensure consistency across codebase</step>
        <step>Add appropriate documentation</step>
      </steps>

    ### Phase: VALIDATION
<description>Verify the implementation</description>
      <steps>
        <step>Check for errors or inconsistencies</step>
        <step>Validate against requirements</step>
        <step>Ensure no regressions</step>
      </steps>

  ## Completion Criteria
- All requirements have been addressed
    - Code follows project conventions
    - Changes are properly documented
    - No breaking changes introduced

    ]]></template>
  </workflow_file_template>

  <best_practices_template>
    <description>Template for best practices files (2_best_practices.xml)</description>
    <template><![CDATA[
<best_practices>
  <general_principles>
    <principle priority="high">
      <name>Principle Name</name>
      <description>Detailed explanation of the principle</description>
      <rationale>Why this principle is important</rationale>
      <example>
        <scenario>When this applies</scenario>
        <good>Correct approach</good>
        <bad>What to avoid</bad>
      </example>
    </principle>
  </general_principles>

  <code_conventions>
    <convention category="naming">
      <rule>Specific naming convention</rule>
      <examples>
        <good>goodExampleName</good>
        <bad>bad_example-name</bad>
      </examples>
    </convention>
    
    <convention category="structure">
      <rule>How to structure code/files</rule>
      <template>
        // Example structure
      </template>
    </convention>
  </code_conventions>

  <common_pitfalls>
    <pitfall>
      <description>Common mistake to avoid</description>
      <why_problematic>Explanation of issues it causes</why_problematic>
      <correct_approach>How to do it properly</correct_approach>
    </pitfall>
  </common_pitfalls>

  <quality_checklist>
    <category name="before_starting">
      <item>Understand requirements fully</item>
      <item>Check existing implementations</item>
    </category>
    <category name="during_implementation">
      <item>Follow established patterns</item>
      <item>Write clear documentation</item>
    </category>
    <category name="before_completion">
      <item>Review all changes</item>
      <item>Verify requirements met</item>
    </category>
  </quality_checklist>
</best_practices>
    ]]></template>
  </best_practices_template>

  <tool_usage_template>
    <description>Template for tool usage files (4_tool_usage.xml)</description>
    <template><![CDATA[
<tool_usage_guide>
  <tool_priorities>
    <priority level="1">
      <tool>codebase_search</tool>
      <when>Always use first to find relevant code</when>
      <why>Semantic search finds functionality better than keywords</why>
    </priority>
    <priority level="2">
      <tool>read_file</tool>
      <when>After identifying files with codebase_search</when>
      <why>Get full context of implementations</why>
    </priority>
  </tool_priorities>

  <tool_specific_guidance>
    <tool name="apply_diff">
      <best_practices>
        <practice>Always read file first to ensure exact content match</practice>
        <practice>Make multiple changes in one diff when possible</practice>
        <practice>Include line numbers for accuracy</practice>
      </best_practices>
      <example><![CDATA[
<apply_diff>
<path>src/config.ts</path>
<diff>
<<<<<<< SEARCH
:start_line:10
-------
export const config = {
  apiUrl: 'http://localhost:3000',
  timeout: 5000
};
=======
export const config = {
  apiUrl: process.env.API_URL || 'http://localhost:3000',
  timeout: parseInt(process.env.TIMEOUT || '5000'),
  retries: 3
};
>>>>>>> REPLACE
</diff>
</apply_diff>
      ]]></example>
    </tool>

    <tool name="ask_followup_question">
      <best_practices>
        <practice>Provide 2-4 specific, actionable suggestions</practice>
        <practice>Order suggestions by likelihood or importance</practice>
        <practice>Make suggestions complete (no placeholders)</practice>
      </best_practices>
      <example><![CDATA[
<ask_followup
