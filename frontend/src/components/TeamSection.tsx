import React from 'react';
import { Layers, Lightbulb, Palette, Users } from 'lucide-react';

const teamMembers = [
  { 
    name: '史尚坤', 
    role: '核心开发', 
    task: '全栈架构设计、任务流调度系统及前后端功能实现', 
    icon: <Layers className="w-4 h-4" /> 
  },
  { 
    name: '杨谨毓', 
    role: '提示词工程师', 
    task: '核心模型 Prompt 调优、学术内容逻辑结构化设计', 
    icon: <Lightbulb className="w-4 h-4" /> 
  },
  { 
    name: '仲星宇', 
    role: '视觉设计', 
    task: '符合 Marp 规范的提示词设计', 
    icon: <Palette className="w-4 h-4" /> 
  },
];

export function TeamSection() {
  return (
    <div className="mt-20 pb-8 animate-in fade-in slide-in-from-bottom-6 duration-1000 delay-200">
      <div className="flex items-center gap-3 justify-center mb-8">
        <div className="h-[1px] w-12 bg-zinc-200 dark:bg-zinc-800" />
        <div className="flex items-center gap-2 text-zinc-400 dark:text-zinc-500">
          <Users className="w-4 h-4" />
          <span className="text-xs font-medium tracking-widest uppercase">Project Contributors</span>
        </div>
        <div className="h-[1px] w-12 bg-zinc-200 dark:bg-zinc-800" />
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {teamMembers.map((member) => (
          <div 
            key={member.name}
            className="group p-5 rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/50 transition-all hover:border-zinc-300 dark:hover:border-zinc-700 hover:shadow-sm"
          >
            <div className="space-y-3">
              <div className="inline-flex p-2.5 rounded-xl bg-zinc-50 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 group-hover:scale-110 transition-transform duration-300">
                {member.icon}
              </div>
              <div>
                <h3 className="font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
                  {member.name}
                  <span className="text-[10px] font-normal px-2 py-0.5 rounded-md bg-zinc-100 dark:bg-zinc-800 text-zinc-500">
                    {member.role}
                  </span>
                </h3>
                <p className="mt-2 text-sm text-zinc-500 dark:text-zinc-400 leading-relaxed">
                  {member.task}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}