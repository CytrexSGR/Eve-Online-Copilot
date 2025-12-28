import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github-dark.css';

interface MarkdownContentProps {
  content: string;
}

export function MarkdownContent({ content }: MarkdownContentProps) {
  return (
    <div className="markdown-content prose prose-invert max-w-none">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          code: ({ inline, className, children, ...props }: any) => {
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
          pre: ({ children, ...props }: any) => (
            <pre
              className="bg-gray-950 p-4 rounded overflow-x-auto border border-gray-700"
              {...props}
            >
              {children}
            </pre>
          ),
          a: ({ href, children, ...props }: any) => (
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
          ul: ({ children, ...props }: any) => (
            <ul className="list-disc list-inside space-y-1" {...props}>
              {children}
            </ul>
          ),
          ol: ({ children, ...props }: any) => (
            <ol className="list-decimal list-inside space-y-1" {...props}>
              {children}
            </ol>
          ),
          blockquote: ({ children, ...props }: any) => (
            <blockquote
              className="border-l-4 border-blue-500 pl-4 italic text-gray-400"
              {...props}
            >
              {children}
            </blockquote>
          ),
          table: ({ children, ...props }: any) => (
            <div className="overflow-x-auto">
              <table className="min-w-full border border-gray-700" {...props}>
                {children}
              </table>
            </div>
          ),
          th: ({ children, ...props }: any) => (
            <th
              className="border border-gray-700 bg-gray-800 px-4 py-2 text-left"
              {...props}
            >
              {children}
            </th>
          ),
          td: ({ children, ...props }: any) => (
            <td className="border border-gray-700 px-4 py-2" {...props}>
              {children}
            </td>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
