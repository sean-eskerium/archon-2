import { useState } from 'react';
import { FileCode, Copy, Check } from 'lucide-react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { useToast } from '../../contexts/ToastContext';

export const IDEGlobalRules = () => {
  const [copied, setCopied] = useState(false);
  const { showToast } = useToast();
  
  const globalRules = `We track the progress of the project via Archon. Use the MCP tool
1. Update all actions to Archon via MCP
2. Make sure to always move tasks from to do, doing, and lastly review, you should not mark tasks complete, until the user has reviewed.
3. Maintain the description of the task item, and add your notes below the description when completing the task.
4. Please DO NOT MAKE ASSUMPTIONS!!!!! For any questions of the project please see the Local Rules.`;

  const handleCopyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(globalRules);
      setCopied(true);
      showToast('Rules copied to clipboard!', 'success');
      
      // Reset copy icon after 2 seconds
      setTimeout(() => {
        setCopied(false);
      }, 2000);
    } catch (err) {
      console.error('Failed to copy text: ', err);
      showToast('Failed to copy to clipboard', 'error');
    }
  };

  return (
    <div>
      <div className="flex items-center mb-4">
        <FileCode className="mr-2 text-blue-500 filter drop-shadow-[0_0_8px_rgba(59,130,246,0.8)]" size={20} />
        <h2 className="text-xl font-semibold text-gray-800 dark:text-white">
          IDE Global Rules
        </h2>
      </div>
      <div className="space-y-6">
        <div className="flex justify-between items-start">
          <p className="text-sm text-gray-600 dark:text-zinc-400 w-4/5">
            Add Global rules to your IDE to increase the consistency of the workflow.
          </p>
          <Button 
            variant="outline" 
            accentColor="blue" 
            icon={copied ? <Check className="w-4 h-4 mr-1" /> : <Copy className="w-4 h-4 mr-1" />}
            className="ml-auto whitespace-nowrap px-4 py-2"
            size="md"
            onClick={handleCopyToClipboard}
          >
            {copied ? 'Copied!' : 'Copy Rules'}
          </Button>
        </div>

        {/* IDE Cards Section */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Cursor Card */}
          <div className="relative p-4 rounded-xl bg-gradient-to-br from-gray-800/30 to-gray-900/20 dark:from-white/30 dark:to-gray-200/20 backdrop-blur-sm border border-gray-500/30 shadow-lg">
            <div className="flex items-center gap-2 mb-2">
              <img src="/img/cursor.svg" alt="Cursor" className="w-5 h-5 filter invert dark:invert-0" />
              <h3 className="text-sm font-semibold text-gray-800 dark:text-white">Cursor</h3>
            </div>
            <p className="text-xs text-gray-600 dark:text-gray-400">
              Create .cursorrules file in project root or use Settings → Rules
            </p>
          </div>

          {/* Windsurf Card */}
          <div className="relative p-4 rounded-xl bg-gradient-to-br from-emerald-500/30 to-green-600/20 backdrop-blur-sm border border-emerald-500/30 shadow-lg">
            <div className="flex items-center gap-2 mb-2">
              <img src="/img/windsurf-white-symbol.svg" alt="Windsurf" className="w-5 h-5" />
              <h3 className="text-sm font-semibold text-gray-800 dark:text-white">Windsurf</h3>
            </div>
            <p className="text-xs text-gray-600 dark:text-gray-400">
              Create .windsurfrules file in project root or use IDE settings
            </p>
          </div>

          {/* Claude Card */}
          <div className="relative p-4 rounded-xl bg-gradient-to-br from-orange-500/30 to-orange-600/20 backdrop-blur-sm border border-orange-500/30 shadow-lg">
            <div className="flex items-center gap-2 mb-2">
              <img src="/img/claude-logo.svg" alt="Claude" className="w-5 h-5" />
              <h3 className="text-sm font-semibold text-gray-800 dark:text-white">Claude</h3>
            </div>
            <p className="text-xs text-gray-600 dark:text-gray-400">
              Create CLAUDE.md file in project root for Claude Desktop integration
            </p>
          </div>
        </div>

        <div className="p-4 border border-blue-200 dark:border-blue-800/30 bg-gradient-to-br from-blue-500/30 to-blue-600/20 backdrop-blur-sm rounded-md">
          <pre className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap font-mono">
            {globalRules}
          </pre>
        </div>

        {/* Security Note */}
        <div className="p-3 bg-gray-50 dark:bg-black/40 rounded-md flex items-start gap-3">
          <div className="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3" />
            </svg>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Adding global rules to your IDE helps maintain consistency across your project and ensures all team members follow the same workflow.
          </p>
        </div>
      </div>
    </div>
  );
};
