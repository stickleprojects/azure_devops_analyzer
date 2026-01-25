-- Migration 005: Rename all FK constraints to explicit names
-- This ensures constraint violations are easier to debug

-- Drop old unnamed constraints and recreate with explicit names

-- projects
ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_organization_id_fkey;
ALTER TABLE projects ADD CONSTRAINT fk_project_organization FOREIGN KEY (organization_id) REFERENCES organizations(organization_id);

-- teams  
ALTER TABLE teams DROP CONSTRAINT IF EXISTS teams_organization_id_fkey;
ALTER TABLE teams ADD CONSTRAINT fk_team_organization FOREIGN KEY (organization_id) REFERENCES organizations(organization_id);

-- repositories
ALTER TABLE repositories DROP CONSTRAINT IF EXISTS repositories_project_id_fkey;
ALTER TABLE repositories DROP CONSTRAINT IF EXISTS repositories_team_id_fkey;
ALTER TABLE repositories ADD CONSTRAINT fk_repository_project FOREIGN KEY (project_id) REFERENCES projects(project_id);
ALTER TABLE repositories ADD CONSTRAINT fk_repository_team FOREIGN KEY (team_id) REFERENCES teams(team_id);

-- branches
ALTER TABLE branches DROP CONSTRAINT IF EXISTS branches_repo_id_fkey;
ALTER TABLE branches ADD CONSTRAINT fk_branch_repository FOREIGN KEY (repo_id) REFERENCES repositories(repo_id) ON DELETE CASCADE;

-- repository_languages
ALTER TABLE repository_languages DROP CONSTRAINT IF EXISTS repository_languages_repo_id_fkey;
ALTER TABLE repository_languages DROP CONSTRAINT IF EXISTS repository_languages_branch_id_fkey;
ALTER TABLE repository_languages ADD CONSTRAINT fk_repolang_repository FOREIGN KEY (repo_id) REFERENCES repositories(repo_id) ON DELETE CASCADE;
ALTER TABLE repository_languages ADD CONSTRAINT fk_repolang_branch FOREIGN KEY (branch_id) REFERENCES branches(branch_id) ON DELETE CASCADE;

-- dependencies
ALTER TABLE dependencies DROP CONSTRAINT IF EXISTS dependencies_repo_id_fkey;
ALTER TABLE dependencies DROP CONSTRAINT IF EXISTS dependencies_branch_id_fkey;
ALTER TABLE dependencies ADD CONSTRAINT fk_dependency_repository FOREIGN KEY (repo_id) REFERENCES repositories(repo_id) ON DELETE CASCADE;
ALTER TABLE dependencies ADD CONSTRAINT fk_dependency_branch FOREIGN KEY (branch_id) REFERENCES branches(branch_id) ON DELETE CASCADE;

-- vulnerabilities
ALTER TABLE vulnerabilities DROP CONSTRAINT IF EXISTS vulnerabilities_dependency_id_fkey;
ALTER TABLE vulnerabilities ADD CONSTRAINT fk_vulnerability_dependency FOREIGN KEY (dependency_id) REFERENCES dependencies(id) ON DELETE CASCADE;

-- code_quality_metrics
ALTER TABLE code_quality_metrics DROP CONSTRAINT IF EXISTS code_quality_metrics_repo_id_fkey;
ALTER TABLE code_quality_metrics DROP CONSTRAINT IF EXISTS code_quality_metrics_branch_id_fkey;
ALTER TABLE code_quality_metrics ADD CONSTRAINT fk_quality_repository FOREIGN KEY (repo_id) REFERENCES repositories(repo_id) ON DELETE CASCADE;
ALTER TABLE code_quality_metrics ADD CONSTRAINT fk_quality_branch FOREIGN KEY (branch_id) REFERENCES branches(branch_id) ON DELETE CASCADE;

-- code_issues
ALTER TABLE code_issues DROP CONSTRAINT IF EXISTS code_issues_repo_id_fkey;
ALTER TABLE code_issues DROP CONSTRAINT IF EXISTS code_issues_branch_id_fkey;
ALTER TABLE code_issues ADD CONSTRAINT fk_issue_repository FOREIGN KEY (repo_id) REFERENCES repositories(repo_id) ON DELETE CASCADE;
ALTER TABLE code_issues ADD CONSTRAINT fk_issue_branch FOREIGN KEY (branch_id) REFERENCES branches(branch_id) ON DELETE CASCADE;

-- repository_summaries
ALTER TABLE repository_summaries DROP CONSTRAINT IF EXISTS repository_summaries_repo_id_fkey;
ALTER TABLE repository_summaries DROP CONSTRAINT IF EXISTS repository_summaries_branch_id_fkey;
ALTER TABLE repository_summaries ADD CONSTRAINT fk_summary_repository FOREIGN KEY (repo_id) REFERENCES repositories(repo_id) ON DELETE CASCADE;
ALTER TABLE repository_summaries ADD CONSTRAINT fk_summary_branch FOREIGN KEY (branch_id) REFERENCES branches(branch_id) ON DELETE CASCADE;

-- readme_files
ALTER TABLE readme_files DROP CONSTRAINT IF EXISTS readme_files_repo_id_fkey;
ALTER TABLE readme_files DROP CONSTRAINT IF EXISTS readme_files_branch_id_fkey;
ALTER TABLE readme_files ADD CONSTRAINT fk_readme_repository FOREIGN KEY (repo_id) REFERENCES repositories(repo_id) ON DELETE CASCADE;
ALTER TABLE readme_files ADD CONSTRAINT fk_readme_branch FOREIGN KEY (branch_id) REFERENCES branches(branch_id) ON DELETE CASCADE;

-- contributors
ALTER TABLE contributors DROP CONSTRAINT IF EXISTS contributors_team_id_fkey;
ALTER TABLE contributors ADD CONSTRAINT fk_contributor_team FOREIGN KEY (team_id) REFERENCES teams(team_id);

-- contributor_metrics
ALTER TABLE contributor_metrics DROP CONSTRAINT IF EXISTS contributor_metrics_repo_id_fkey;
ALTER TABLE contributor_metrics DROP CONSTRAINT IF EXISTS contributor_metrics_contributor_id_fkey;
ALTER TABLE contributor_metrics ADD CONSTRAINT fk_contribmetrics_repository FOREIGN KEY (repo_id) REFERENCES repositories(repo_id) ON DELETE CASCADE;
ALTER TABLE contributor_metrics ADD CONSTRAINT fk_contribmetrics_contributor FOREIGN KEY (contributor_id) REFERENCES contributors(id) ON DELETE CASCADE;

-- commits
ALTER TABLE commits DROP CONSTRAINT IF EXISTS commits_repo_id_fkey;
ALTER TABLE commits DROP CONSTRAINT IF EXISTS commits_author_id_fkey;
ALTER TABLE commits DROP CONSTRAINT IF EXISTS commits_committer_id_fkey;
ALTER TABLE commits ADD CONSTRAINT fk_commit_repository FOREIGN KEY (repo_id) REFERENCES repositories(repo_id) ON DELETE CASCADE;
ALTER TABLE commits ADD CONSTRAINT fk_commit_author FOREIGN KEY (author_id) REFERENCES contributors(id);
ALTER TABLE commits ADD CONSTRAINT fk_commit_committer FOREIGN KEY (committer_id) REFERENCES contributors(id);

-- pull_requests
ALTER TABLE pull_requests DROP CONSTRAINT IF EXISTS pull_requests_repo_id_fkey;
ALTER TABLE pull_requests DROP CONSTRAINT IF EXISTS pull_requests_author_id_fkey;
ALTER TABLE pull_requests ADD CONSTRAINT fk_pr_repository FOREIGN KEY (repo_id) REFERENCES repositories(repo_id) ON DELETE CASCADE;
ALTER TABLE pull_requests ADD CONSTRAINT fk_pr_author FOREIGN KEY (author_id) REFERENCES contributors(id);

-- pr_reviews
ALTER TABLE pr_reviews DROP CONSTRAINT IF EXISTS pr_reviews_pr_id_fkey;
ALTER TABLE pr_reviews DROP CONSTRAINT IF EXISTS pr_reviews_reviewer_id_fkey;
ALTER TABLE pr_reviews ADD CONSTRAINT fk_review_pr FOREIGN KEY (pr_id) REFERENCES pull_requests(id) ON DELETE CASCADE;
ALTER TABLE pr_reviews ADD CONSTRAINT fk_review_reviewer FOREIGN KEY (reviewer_id) REFERENCES contributors(id);

-- pr_comments
ALTER TABLE pr_comments DROP CONSTRAINT IF EXISTS pr_comments_pr_id_fkey;
ALTER TABLE pr_comments DROP CONSTRAINT IF EXISTS pr_comments_author_id_fkey;
ALTER TABLE pr_comments ADD CONSTRAINT fk_comment_pr FOREIGN KEY (pr_id) REFERENCES pull_requests(id) ON DELETE CASCADE;
ALTER TABLE pr_comments ADD CONSTRAINT fk_comment_author FOREIGN KEY (author_id) REFERENCES contributors(id);

-- branch_metrics
ALTER TABLE branch_metrics DROP CONSTRAINT IF EXISTS branch_metrics_branch_id_fkey;
ALTER TABLE branch_metrics ADD CONSTRAINT fk_branchmetrics_branch FOREIGN KEY (branch_id) REFERENCES branches(branch_id) ON DELETE CASCADE;

-- repository_services
ALTER TABLE repository_services DROP CONSTRAINT IF EXISTS repository_services_repo_id_fkey;
ALTER TABLE repository_services DROP CONSTRAINT IF EXISTS repository_services_service_id_fkey;
ALTER TABLE repository_services ADD CONSTRAINT fk_reposervice_repository FOREIGN KEY (repo_id) REFERENCES repositories(repo_id) ON DELETE CASCADE;
ALTER TABLE repository_services ADD CONSTRAINT fk_reposervice_service FOREIGN KEY (service_id) REFERENCES services(service_id) ON DELETE CASCADE;
