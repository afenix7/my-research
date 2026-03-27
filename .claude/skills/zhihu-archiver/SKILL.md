---
name: zhihu-archiver
description: Archive Zhihu (知乎) column articles to this research repository. Use this skill whenever the user provides a URL containing zhihu.com or mentions "知乎" / "知乎专栏" and wants to save the article content. This skill uses agent-browser to access the article, handles login verification by taking screenshots for QR code login, extracts the full article content, and saves it categorized by topic into the ./zhihu/ directory structure matching the repository's existing topic categories.
---

# Zhihu Archiver Skill

Archiving Zhihu column articles to the local research repository using agent-browser.

## Trigger Conditions

Use this skill when:
- User provides a link containing `zhihu.com` or `zhuanlan.zhihu.com`
- User mentions "知乎" / "知乎专栏" and wants to save an article
- User asks to archive or download a Zhihu article

## Workflow

### Step 1: Verify Input
- Extract the URL from the user's message. If no URL is provided but "zhihu" is mentioned, ask user for the specific article link.
- Determine the topic category based on article content:
  - `agents` - AI agent frameworks, LLM agents, autonomous agents
  - `render-graph` - Game engine render graphs, rendering, graphics
  - `ecs` - Entity Component System, game architecture
  - `finance` - Quantitative finance, algorithmic trading, markets
  - `intel` - Industry analysis, technology intelligence, semiconductor
  - `claw` - Claw ecosystem research
  - `marketing` - Marketing, growth, business strategy
  - `notes` - General technical notes, miscellaneous

### Step 2: Access with agent-browser
1.  Use the `agent-browser` skill to navigate to the Zhihu article URL:
    ```
    /agent-browser navigate <URL>
    ```
2.  Wait for the page to load completely.

### Step 3: Check for Login/Verification
1.  Try to extract the main article content. If content is not accessible (blocked by login):
    - Create `/root/my-research/tmp` directory if it doesn't exist: `mkdir -p /root/my-research/tmp`
    - Take an annotated screenshot:
      ```
      /agent-browser snapshot --annotate /root/my-research/tmp/zhihu_login.png
      ```
    - Add and commit the screenshot:
      ```bash
      git add /root/my-research/tmp/zhihu_login.png
      git commit -m "feat: add zhihu login screenshot for QR code authentication"
      git push
      ```
    - Inform the user: "I've pushed the login screenshot to the repository. Please pull, scan the QR code at `tmp/zhihu_login.png` to log in, then let me know when done."
    - Wait for user confirmation that login is complete.
    - After confirmation, reload the page and check again:
      ```
      /agent-browser snapshot -i
      ```
2.  If already logged in or no login required, proceed directly to content extraction.

### Step 4: Extract Article Content
1.  Use agent-browser to extract the full article content:
    ```
    /agent-browser eval "document.querySelector('.RichContent').innerText"
    ```
    Or if that selector fails:
    ```
    /agent-browser eval "document.querySelector('article').innerText"
    ```
2.  Get the article title:
    ```
    /agent-browser eval "document.querySelector('h1').innerText"
    ```

### Step 5: Save to Repository
1.  Create the target directory if it doesn't exist:
    - Topic directory: `/root/my-research/zhihu/{topic}/`
    ```bash
    mkdir -p "/root/my-research/zhihu/{topic}"
    ```
2.  Clean the article title to create a valid filename (remove special characters, replace spaces with hyphens)
3.  Save the content with frontmatter:
    ```markdown
    ---
    title: {Article Title}
    original_url: {Original URL}
    archived_at: {Current Date (YYYY-MM-DD)}
    topic: {Topic}
    ---

    {Extracted Article Content}
    ```
4.  Write to: `/root/my-research/zhihu/{topic}/{cleaned-title}.md`

### Step 6: Commit and Push
1.  Add the new file to git
2.  Commit with message: `archived: add zhihu article "{title}" to {topic}`
3.  Push to remote
4.  Inform the user the article has been archived successfully with the full path.

## Notes

- The base research repository is at `/root/my-research/`, always use absolute paths.
- If agent-browser commands fail, try alternative selectors for content extraction.
- Always confirm the topic category with the user if uncertain before saving.
