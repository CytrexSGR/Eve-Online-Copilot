import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import type { Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github-dark.css';

interface MarkdownContentProps {
  content: string;
}

interface CodeProps {
  inline?: boolean;
  className?: string;
  children?: React.ReactNode;
}

interface ElementProps {
  children?: React.ReactNode;
  href?: string;
}

export function MarkdownContent({ content }: MarkdownContentProps) {
  const [error, setError] = useState<string | null>(null);

  // Custom components with proper TypeScript types
  const components: Components = {
    code: ({ inline, className, children, ...props }: CodeProps) => {
      return !inline ? (
        <code className={className} {...props}>
          {children}
        </code>
      ) : (
        <code
          className="bg-gray-900 px-1.5 py-0.5 rounded text-sm text-yellow-400"
          {...props}
        >
          {children}
        </code>
      );
    },
    pre: ({ children, ...props }: ElementProps) => (
      <pre
        className="bg-gray-950 p-4 rounded overflow-x-auto border border-gray-700"
        {...props}
      >
        {children}
      </pre>
    ),
    a: ({ href, children, ...props }: ElementProps) => (
      <a
        href={href}
        className="text-blue-400 hover:text-blue-300 underline"
        target="_blank"
        rel="noopener noreferrer"
        {...props}
      >
        {children}
      </a>
    ),
    ul: ({ children, ...props }: ElementProps) => (
      <ul className="list-disc list-inside space-y-1" {...props}>
        {children}
      </ul>
    ),
    ol: ({ children, ...props }: ElementProps) => (
      <ol className="list-decimal list-inside space-y-1" {...props}>
        {children}
      </ol>
    ),
    blockquote: ({ children, ...props }: ElementProps) => (
      <blockquote
        className="border-l-4 border-blue-500 pl-4 italic text-gray-400"
        {...props}
      >
        {children}
      </blockquote>
    ),
    table: ({ children, ...props }: ElementProps) => (
      <div className="overflow-x-auto">
        <table className="min-w-full border border-gray-700" {...props}>
          {children}
        </table>
      </div>
    ),
    th: ({ children, ...props }: ElementProps) => (
      <th
        className="border border-gray-700 bg-gray-800 px-4 py-2 text-left"
        {...props}
      >
        {children}
      </th>
    ),
    td: ({ children, ...props }: ElementProps) => (
      <td className="border border-gray-700 px-4 py-2" {...props}>
        {children}
      </td>
    ),
  };

  // Error handling: try to render markdown, fallback to plain text
  try {
    return (
      <div className="markdown-content prose prose-invert max-w-none">
        {error ? (
          <div className="text-gray-300 whitespace-pre-wrap">{content}</div>
        ) : (
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeHighlight]}
            components={components}
          >
            {content}
          </ReactMarkdown>
        )}
      </div>
    );
  } catch (err) {
    // Log error and gracefully degrade to plain text
    console.error('Markdown rendering error:', err);
    setError(err instanceof Error ? err.message : 'Unknown error');

    return (
      <div className="markdown-content prose prose-invert max-w-none">
        <div className="text-gray-300 whitespace-pre-wrap">{content}</div>
      </div>
    );
  }
}
