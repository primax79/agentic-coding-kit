const fs = require('fs');
const path = require('path');

function ensureDirSync(dirPath) {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
}

function copyRecursiveSync(src, dest) {
  const exists = fs.existsSync(src);
  const stats = exists && fs.statSync(src);
  const isDirectory = exists && stats.isDirectory();
  if (isDirectory) {
    ensureDirSync(dest);
    fs.readdirSync(src).forEach((childItemName) => {
      copyRecursiveSync(path.join(src, childItemName), path.join(dest, childItemName));
    });
  } else {
    fs.copyFileSync(src, dest);
  }
}

// Simple XML to Markdown converter for Roo Rules XML format
function convertXmlToMarkdown(xmlContent) {
  let md = xmlContent;
  
  // Replace XML tags with Markdown headers/lists/formatting
  // Remove wrapping tags or translate them
  md = md.replace(/<workflow_instructions>|<\/workflow_instructions>/gi, '');
  md = md.replace(/<mode_overview>([\s\S]*?)<\/mode_overview>/gi, (m, content) => {
    return `## Mode Overview\n${content.trim()}\n\n`;
  });
  
  md = md.replace(/<operating_principles>([\s\S]*?)<\/operating_principles>/gi, (m, content) => {
    let inner = content.trim();
    inner = inner.replace(/<principle>([\s\S]*?)<\/principle>/gi, '- $1');
    return `## Operating Principles\n${inner}\n\n`;
  });

  md = md.replace(/<preambles>([\s\S]*?)<\/preambles>/gi, (m, content) => {
    let inner = content.trim();
    inner = inner.replace(/<rule>([\s\S]*?)<\/rule>/gi, '- $1');
    return `## Preambles / Core Rules\n${inner}\n\n`;
  });

  md = md.replace(/<discovery_and_budgets>([\s\S]*?)<\/discovery_and_budgets>/gi, (m, content) => {
    let inner = content.trim();
    inner = inner.replace(/<early_stop>([\s\S]*?)<\/early_stop>/gi, '- **Early Stop**: $1');
    inner = inner.replace(/<budget>([\s\S]*?)<\/budget>/gi, '- **Budget**: $1');
    inner = inner.replace(/<escalate_once>([\s\S]*?)<\/escalate_once>/gi, '- **Escalate Once**: $1');
    return `## Discovery and Budgets\n${inner}\n\n`;
  });

  md = md.replace(/<main_workflow>([\s\S]*?)<\/main_workflow>/gi, (m, content) => {
    return `## Main Workflow\n${content.trim()}\n\n`;
  });

  md = md.replace(/<phase\s+name="([^"]+)">([\s\S]*?)<\/phase>/gi, (m, name, content) => {
    return `### Phase: ${name.toUpperCase()}\n${content.trim()}\n\n`;
  });

  md = md.replace(/<step\s+number="([^"]+)">([\s\S]*?)<\/step>/gi, (m, num, content) => {
    let inner = content.trim();
    let title = '';
    inner = inner.replace(/<title>([\s\S]*?)<\/title>/gi, (m2, t) => {
      title = t.trim();
      return '';
    });
    
    inner = inner.replace(/<actions>([\s\S]*?)<\/actions>/gi, (m2, acts) => {
      return `#### Actions:\n` + acts.trim().replace(/<action>([\s\S]*?)<\/action>/gi, '- $1');
    });

    inner = inner.replace(/<acceptance_criteria>([\s\S]*?)<\/acceptance_criteria>/gi, (m2, ac) => {
      return `#### Acceptance Criteria:\n` + ac.trim().replace(/<criterion>([\s\S]*?)<\/criterion>/gi, '- $1');
    });

    inner = inner.replace(/<quality_gates>([\s\S]*?)<\/quality_gates>/gi, (m2, qg) => {
      return `#### Quality Gates:\n` + qg.trim().replace(/<gate>([\s\S]*?)<\/gate>/gi, '- $1');
    });

    inner = inner.replace(/<checks>([\s\S]*?)<\/checks>/gi, (m2, chk) => {
      return `#### Validation Checks:\n` + chk.trim().replace(/<check>([\s\S]*?)<\/check>/gi, '- $1');
    });

    return `#### Step ${num}: ${title}\n${inner.trim()}\n\n`;
  });

  md = md.replace(/<completion_criteria>([\s\S]*?)<\/completion_criteria>/gi, (m, content) => {
    let inner = content.trim();
    inner = inner.replace(/<criterion>([\s\S]*?)<\/criterion>/gi, '- $1');
    return `## Completion Criteria\n${inner}\n\n`;
  });

  // Cleanup extra whitespace
  md = md.replace(/\n{3,}/g, '\n\n').trim();
  return md;
}

function migrate(sourceRoot, targetRoot, isGlobal) {
  console.log(`\n=== Migrating ${isGlobal ? 'Global' : 'Local'} Configurations ===`);
  console.log(`Source: ${sourceRoot}`);
  console.log(`Target: ${targetRoot}`);

  if (!fs.existsSync(sourceRoot)) {
    console.log(`Source directory does not exist: ${sourceRoot}. Skipping.`);
    return;
  }

  // Ensure target directories exist
  const skillsTargetDir = path.join(targetRoot, 'skills');
  const agentTargetDir = path.join(targetRoot, 'agent');
  ensureDirSync(skillsTargetDir);
  ensureDirSync(agentTargetDir);

  // 1. Migrate Skills
  const sourceSkillsDir = path.join(sourceRoot, 'skills');
  if (fs.existsSync(sourceSkillsDir)) {
    const skills = fs.readdirSync(sourceSkillsDir);
    skills.forEach(skillName => {
      if (skillName.startsWith('.')) return;
      const skillSrc = path.join(sourceSkillsDir, skillName);
      if (fs.statSync(skillSrc).isDirectory()) {
        const skillDest = path.join(skillsTargetDir, skillName);
        console.log(`- Migrating Skill: ${skillName}`);
        copyRecursiveSync(skillSrc, skillDest);
      }
    });
  }

  // 2. Migrate Rules/Modes -> Agents
  const files = fs.readdirSync(sourceRoot);
  files.forEach(fileName => {
    if (fileName.startsWith('rules-')) {
      const modeName = fileName.replace('rules-', '');
      const rulesSrcDir = path.join(sourceRoot, fileName);
      if (fs.statSync(rulesSrcDir).isDirectory()) {
        console.log(`- Migrating Mode Rules: ${modeName}`);
        
        // Read all XML/rules files inside rules-X folder
        const ruleFiles = fs.readdirSync(rulesSrcDir)
          .filter(f => !f.startsWith('.') && (f.endsWith('.xml') || f.endsWith('.md')))
          .sort(); // Sort so 1_workflow.xml comes before 2_best_practices.xml, etc.

        let compiledPrompt = '';
        ruleFiles.forEach(ruleFile => {
          const ruleFilePath = path.join(rulesSrcDir, ruleFile);
          const rawContent = fs.readFileSync(ruleFilePath, 'utf8');
          
          compiledPrompt += `### Rules from: ${ruleFile}\n\n`;
          if (ruleFile.endsWith('.xml')) {
            compiledPrompt += convertXmlToMarkdown(rawContent) + '\n\n';
          } else {
            compiledPrompt += rawContent + '\n\n';
          }
        });

        const agentFileName = `${modeName}.md`;
        const agentFilePath = path.join(agentTargetDir, agentFileName);
        
        const agentFileContent = `---
name: ${modeName}
description: Migrated Roocode Mode rules for ${modeName}
mode: primary
permission:
  read: allow
  edit: allow
  bash: allow
  mcp: allow
---

# ${modeName.toUpperCase()} Agent Rules

${compiledPrompt.trim()}
`;

        fs.writeFileSync(agentFilePath, agentFileContent, 'utf8');
        console.log(`  Created Agent: ${agentFilePath}`);
      }
    }
  });
}

// Global migration
const globalSource = path.join(process.env.HOME || '/Users/Alfredo', '.roo');
const globalTarget = path.join(process.env.HOME || '/Users/Alfredo', '.config', 'kilo');
migrate(globalSource, globalTarget, true);

// Local migration
const localSource = path.join(process.cwd(), '.roo');
const localTarget = path.join(process.cwd(), '.kilo');
migrate(localSource, localTarget, false);

console.log('\nMigration complete successfully!');
